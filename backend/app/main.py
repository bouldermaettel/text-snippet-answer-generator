"""FastAPI app: /api/ask, /api/snippets, /api/auth, /api/users."""
import io
import json
import logging
import os
import re
import shutil
import tarfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, File, Form, FastAPI, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .auth import authenticate_user, create_access_token, get_current_admin, get_current_user
from .config import get_settings
from .generation import generate_answer, refine_answer
from .models import (
    AskRequest,
    AskResponse,
    CollectionGroupedItem,
    PromptItem,
    PromptUpdate,
    RefineRequest,
    RefineResponse,
    SnippetCreate,
    SnippetGroupItem,
    SnippetGroupListResponse,
    SnippetGroupUpdate,
    SnippetItem,
    SnippetListResponse,
    SnippetUpdate,
    ExampleQuestionsUpdate,
    SourceItem,
    TokenResponse,
    TranslationEntry,
    UserCreate,
    UserCreateAdmin,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from .retrieval import answer_confidence, retrieve_and_score
from .store import add_snippets, delete_snippet, delete_snippets_by_group, get_linked_snippets, get_snippet_metadata, list_groups, list_snippets, list_snippets_grouped, update_example_questions, update_snippet, update_snippet_grouped
from .anonymize import anonymize_text
from .upload import extract_text_from_bytes
from .user_store import count_admins, create_user, delete_user, get_user_by_email, get_user_by_id, init_db, list_users, set_user_role, set_user_status


def _strip_env_value(s: str | None) -> str | None:
    """Strip whitespace and remove inline # comments (common .env mistake)."""
    if s is None:
        return None
    s = s.strip()
    if "#" in s:
        s = s.split("#", 1)[0].strip()
    return s if s else None


def _seed_admin_if_needed() -> None:
    settings = get_settings()
    if count_admins() > 0:
        return
    raw_email = _strip_env_value(settings.admin_email)
    raw_password = _strip_env_value(settings.admin_password)
    if not raw_email or not raw_password:
        return
    email = raw_email.lower()
    if get_user_by_email(email):
        return
    create_user(email, raw_password, role="admin")
    logging.info("Seeded initial admin user: %s", email)


def _configure_logging() -> None:
    """Set up structured JSON logging in production for Azure Monitor integration."""
    settings = get_settings()
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    if settings.environment.lower() == "production":
        import json as _json

        class _JsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                log_record = {
                    "timestamp": self.formatTime(record, self.datefmt),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                if record.exc_info and record.exc_info[1]:
                    log_record["exception"] = self.formatException(record.exc_info)
                return _json.dumps(log_record)

        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter())
        logging.root.handlers.clear()
        logging.root.addHandler(handler)
        logging.root.setLevel(level)
    else:
        logging.basicConfig(level=level, format="%(levelname)s: %(name)s: %(message)s")


def _enforce_jwt_secret() -> None:
    """Raise if JWT_SECRET is still the default in production."""
    settings = get_settings()
    if settings.environment.lower() == "production" and settings.jwt_secret == "change-me-in-production":
        raise RuntimeError(
            "FATAL: JWT_SECRET must be set to a secure value in production. "
            "Set the JWT_SECRET environment variable."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _enforce_jwt_secret()
    _configure_logging()
    init_db()
    _seed_admin_if_needed()
    yield


app = FastAPI(title="RAG Snippet Answer API", lifespan=lifespan)

# CORS: configurable via ALLOWED_ORIGINS env var.
# In single-container production (frontend served from same origin) this is a no-op.
_settings_cors = get_settings()
_origins = [o.strip() for o in _settings_cors.allowed_origins.split(",") if o.strip()]
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@app.post("/api/auth/register")
def register(payload: UserCreate):
    """Register a new user (status=pending). Admin must approve before login."""
    email = payload.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email already registered")
    create_user(email, payload.password, role="user", status="pending")
    return {"message": "Registration submitted. An administrator will approve your account."}


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: UserLogin):
    """Login with email/password. Returns JWT only if user status is active."""
    user = authenticate_user(payload.email.strip().lower(), payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user.get("status") != "active":
        raise HTTPException(status_code=403, detail="Account pending approval")
    token = create_access_token(user["id"], user["email"], user["role"])
    return TokenResponse(access_token=token)


@app.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: Annotated[dict, Depends(get_current_user)]):
    """Return current user (id, email, role, status)."""
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        role=current_user["role"],
        status=current_user.get("status", "active"),
        created_at=current_user.get("created_at"),
    )


@app.post("/api/ask", response_model=AskResponse)
def ask(
    req: AskRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Retrieve relevant snippets, generate answer, return answer + sources + confidence."""
    sources = retrieve_and_score(
        req.question,
        top_k=5,
        group_names=req.group_names,
        snippet_ids=req.snippet_ids,
        languages=req.languages,
        use_hyde=req.use_hyde,
        use_keyword_rerank=req.use_keyword_rerank,
    )
    if not sources:
        return AskResponse(
            answer="No relevant snippets in the knowledge base. Add snippets first.",
            sources=[],
            answer_confidence=0.0,
        )
    snippet_texts = [s["text"] for s in sources]
    answer_text, section_labels = generate_answer(
        req.question, snippet_texts, settings=get_settings(), answer_closeness=req.answer_closeness
    )
    confidences = [s["snippet_confidence"] for s in sources]
    ans_conf = answer_confidence(confidences)
    n = len(sources)
    section_list = (section_labels + [None] * n)[:n]
    return AskResponse(
        answer=answer_text,
        sources=[
            SourceItem(
                id=s["id"],
                text=s["text"],
                title=s.get("title"),
                snippet_confidence=s["snippet_confidence"],
                source_document_url=(s.get("metadata") or {}).get("source_document_url"),
                section_label=section_list[i] if i < len(section_list) else None,
                metadata=s.get("metadata"),
            )
            for i, s in enumerate(sources)
        ],
        answer_confidence=ans_conf,
    )


@app.post("/api/refine", response_model=RefineResponse)
def refine(
    req: RefineRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
):
    """Refine an existing answer based on user feedback and selected snippets."""
    # Filter sources to only include selected ones, or use all if none selected
    if req.selected_source_ids:
        selected_sources = [s for s in req.sources if s.id in req.selected_source_ids]
    else:
        selected_sources = req.sources

    if not selected_sources:
        return RefineResponse(
            answer=req.original_answer,
            sources=[],
            answer_confidence=0.0,
        )

    snippet_texts = [s.text for s in selected_sources]
    refined_answer = refine_answer(
        original_question=req.original_question,
        original_answer=req.original_answer,
        refinement_prompt=req.refinement_prompt,
        snippet_texts=snippet_texts,
        settings=get_settings(),
        answer_closeness=req.answer_closeness,
    )

    # Calculate confidence based on selected sources
    confidences = [s.snippet_confidence for s in selected_sources]
    ans_conf = answer_confidence(confidences)

    return RefineResponse(
        answer=refined_answer,
        sources=selected_sources,
        answer_confidence=ans_conf,
    )


@app.get("/api/snippets")
def get_snippets(
    limit: int = 100,
    offset: int = 0,
    group: Annotated[list[str] | None, Query()] = None,
    language: Annotated[list[str] | None, Query()] = None,
    include_translations: bool = False,
    grouped: bool = False,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """List snippets (paginated). Optional filters: group(s), language(s).

    If ``grouped=true``, returns snippets with nested translations dict
    (``SnippetGroupListResponse``).  Otherwise returns the flat list
    (``SnippetListResponse``).
    """
    if grouped:
        snippets, total = list_snippets_grouped(
            limit=limit,
            offset=offset,
            group_names=group if group and len(group) > 0 else None,
            languages=language if language and len(language) > 0 else None,
        )
        return SnippetGroupListResponse(
            snippets=[
                SnippetGroupItem(
                    id=s["id"],
                    title=s.get("title"),
                    group=s.get("group"),
                    metadata=s.get("metadata"),
                    translations={
                        lang: TranslationEntry(
                            text=tr["text"],
                            example_questions=tr.get("example_questions", []),
                            is_generated_translation=tr.get("is_generated_translation", False),
                        )
                        for lang, tr in (s.get("translations") or {}).items()
                    },
                )
                for s in snippets
            ],
            total=total,
        )

    snippets, total = list_snippets(
        limit=limit,
        offset=offset,
        group_names=group if group and len(group) > 0 else None,
        languages=language if language and len(language) > 0 else None,
        include_translations=include_translations,
    )
    return SnippetListResponse(
        snippets=[
            SnippetItem(
                id=s["id"],
                text=s["text"],
                title=s.get("title"),
                group=s.get("group"),
                metadata=s.get("metadata"),
            )
            for s in snippets
        ],
        total=total,
    )


@app.get("/api/groups")
def get_groups(
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """List distinct group names."""
    return {"groups": list_groups()}


@app.get("/api/settings/default-closing")
def get_default_closing(
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Return the configurable default closing greeting for answers."""
    from .prompt_store import get_prompt
    return {"closing": get_prompt("default_closing")}


@app.post("/api/snippets")
def post_snippets(
    payload: SnippetCreate | list[SnippetCreate],
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Add one or more snippets. If anonymize=True on any item, PII is replaced with placeholders.
    If skip_translation=True on any item, LLM translation generation is skipped."""
    settings = get_settings()
    payloads = payload if isinstance(payload, list) else [payload]
    items: list[dict] = []
    any_skip_translation = False
    for p in payloads:
        text = p.text
        metadata = dict(p.metadata) if p.metadata else {}
        if p.anonymize and settings.enable_pii_anonymization:
            text = anonymize_text(text, settings)
            metadata["anonymized"] = True
        if p.skip_translation:
            any_skip_translation = True
        items.append({
            "text": text,
            "title": p.title,
            "metadata": metadata if metadata else None,
            "group": p.group,
        })
    ids = add_snippets(items, skip_translation=any_skip_translation)
    return {"ids": ids, "count": len(ids)}


@app.post("/api/snippets/grouped")
def post_snippet_grouped(
    payload: CollectionGroupedItem,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Create a single grouped snippet with multiple language translations.

    Accepts the same grouped format used by import/export: a title, group,
    shared metadata, and a ``translations`` dict keyed by language code.
    Unlike import, this does **not** replace existing snippets in the group.
    """
    from .store import _chunk_text, _get_collection, _index_example_questions
    from .embeddings import embed

    originals = {
        lang: tr for lang, tr in payload.translations.items()
        if not tr.is_generated_translation
    }
    generated = {
        lang: tr for lang, tr in payload.translations.items()
        if tr.is_generated_translation
    }

    if not originals:
        raise HTTPException(status_code=400, detail="At least one non-generated translation is required")

    settings = get_settings()
    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap
    coll = _get_collection()

    first_lang = next(iter(originals))
    first_tr = originals[first_lang]

    shared_meta = dict(payload.metadata) if payload.metadata else {}
    shared_meta["language"] = first_lang
    if first_tr.example_questions:
        shared_meta["example_questions"] = first_tr.example_questions

    if len(originals) > 1:
        all_titles = [f"{payload.title}-{lang}" for lang in originals]
        shared_meta["linked_snippets"] = [
            t for t in all_titles if t != f"{payload.title}-{first_lang}"
        ]

    items = [{
        "text": first_tr.text,
        "title": payload.title,
        "metadata": shared_meta,
        "group": payload.group,
    }]
    ids = add_snippets(items, skip_translation=True)
    parent_id = ids[0]

    if first_tr.example_questions:
        _index_example_questions(
            parent_id, first_tr.example_questions, payload.title, payload.group
        )

    remaining_originals = {
        lang: tr for lang, tr in originals.items() if lang != first_lang
    }
    all_extra = {**remaining_originals, **generated}
    translation_count = 0

    for lang, tr in all_extra.items():
        tr_text = tr.text.strip()
        if not tr_text:
            continue

        is_gen = tr.is_generated_translation or lang in generated
        chunks = _chunk_text(tr_text, chunk_size, overlap)
        tr_ids: list[str] = []
        tr_docs: list[str] = []
        tr_metas: list[dict] = []
        for idx, chunk in enumerate(chunks):
            base_id = f"{parent_id}_tr_{lang}"
            doc_id = base_id if len(chunks) == 1 else f"{base_id}_{idx}"
            chunk_meta: dict[str, Any] = {
                "title": payload.title,
                "parent_id": parent_id,
                "chunk_index": str(idx),
                "group": payload.group,
                "original_language": first_lang,
                "translation_language": lang,
                "is_translation": "true",
            }
            enriched: dict[str, Any] = dict(shared_meta)
            enriched["language"] = lang
            enriched.pop("linked_snippets", None)
            enriched.pop("example_questions", None)
            if tr.example_questions:
                enriched["example_questions"] = tr.example_questions
            enriched["translation_source"] = "generated" if is_gen else "original"
            chunk_meta["metadata_json"] = json.dumps(enriched)
            tr_ids.append(doc_id)
            tr_docs.append(chunk)
            tr_metas.append(chunk_meta)

        if tr_ids:
            embeddings = embed(tr_docs).tolist()
            coll.add(ids=tr_ids, embeddings=embeddings, documents=tr_docs, metadatas=tr_metas)
            translation_count += 1

        if tr.example_questions:
            _index_example_questions(
                f"{parent_id}_tr_{lang}", tr.example_questions, payload.title, payload.group
            )

    return {
        "id": parent_id,
        "languages": list(payload.translations.keys()),
        "translation_count": translation_count,
    }


@app.patch("/api/snippets/{snippet_id}")
def patch_snippet(
    snippet_id: str,
    payload: SnippetUpdate,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Update a snippet by id (flat single-language update)."""
    update_snippet(snippet_id, payload.text, payload.title, metadata=payload.metadata, group=payload.group)
    return {"ok": True}


@app.put("/api/snippets/{snippet_id}/group")
def put_snippet_group(
    snippet_id: str,
    payload: SnippetGroupUpdate,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Update a snippet group (shared metadata + all translations)."""
    translations_dict = None
    if payload.translations is not None:
        translations_dict = {
            lang: {
                "text": tr.text,
                "example_questions": tr.example_questions,
                "is_generated_translation": tr.is_generated_translation,
            }
            for lang, tr in payload.translations.items()
        }
    ok = update_snippet_grouped(
        snippet_id,
        title=payload.title,
        group=payload.group,
        metadata=dict(payload.metadata) if payload.metadata else None,
        translations=translations_dict,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return {"ok": True}


@app.delete("/api/snippets/{snippet_id}")
def delete_snippet_endpoint(
    snippet_id: str,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Delete a snippet by id."""
    delete_snippet(snippet_id)
    settings = get_settings()
    if settings.upload_dir:
        upload_path = Path(settings.upload_dir) / snippet_id
        if upload_path.exists() and upload_path.is_dir():
            shutil.rmtree(upload_path, ignore_errors=True)
    return {"ok": True}


@app.put("/api/snippets/{snippet_id}/example-questions")
def update_snippet_example_questions(
    snippet_id: str,
    payload: ExampleQuestionsUpdate,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Update example questions for a snippet (original or translation).
    
    This allows editing example questions for any snippet, including
    auto-translated snippets (IDs containing _tr_).
    """
    update_example_questions(snippet_id, payload.example_questions)
    return {"ok": True}


def _sanitize_filename(filename: str) -> str:
    """Keep basename and allow only safe chars (alphanumeric, dot, hyphen, underscore)."""
    base = Path(filename).name
    safe = re.sub(r"[^\w.\-]", "_", base)
    return safe or "document"


def _content_type_for_filename(filename: str) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return "application/pdf"
    if name.endswith(".docx"):
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/octet-stream"


@app.get("/api/snippets/{snippet_id}/document")
def get_snippet_document(
    snippet_id: str,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Serve the stored original document for a snippet (PDF/DOCX) if it exists."""
    settings = get_settings()
    if not settings.upload_dir:
        raise HTTPException(status_code=404, detail="Document storage not configured")
    upload_path = Path(settings.upload_dir) / snippet_id
    if not upload_path.exists() or not upload_path.is_dir():
        raise HTTPException(status_code=404, detail="Document not found")
    files = [f for f in upload_path.iterdir() if f.is_file()]
    if not files:
        raise HTTPException(status_code=404, detail="Document not found")
    path = files[0]
    media_type = _content_type_for_filename(path.name)
    return FileResponse(path, media_type=media_type, filename=path.name)


@app.get("/api/snippets/{snippet_id}/linked")
def get_snippet_linked(
    snippet_id: str,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Get all linked translations for a snippet.
    
    Uses the 'linked_snippets' field in metadata to fetch related snippets in other languages.
    Returns list of snippets including the original.
    """
    linked = get_linked_snippets(snippet_id)
    return {
        "snippets": [
            SnippetItem(
                id=s["id"],
                text=s["text"],
                title=s.get("title"),
                group=s.get("group"),
                metadata=s.get("metadata"),
            )
            for s in linked
        ]
    }


@app.post("/api/snippets/upload")
def upload_snippets(
    files: list[UploadFile] = File(...),
    group: str | None = Form(None),
    anonymize: bool = Form(False),
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Upload .txt, .docx, or .pdf files; each file becomes one snippet. Title = filename (no extension).
    If anonymize=True, PII (names, addresses, etc.) is replaced with generic placeholders."""
    items: list[dict] = []
    file_data: list[tuple[bytes, str]] = []  # (content, filename) for PDF/DOCX only
    errors = []
    settings = get_settings()
    upload_dir = Path(settings.upload_dir) if settings.upload_dir else None
    do_anonymize = anonymize and settings.enable_pii_anonymization

    for f in files:
        if not f.filename:
            continue
        name = f.filename.lower()
        if not (name.endswith(".txt") or name.endswith(".docx") or name.endswith(".pdf")):
            errors.append(f"{f.filename}: only .txt, .docx, and .pdf are allowed")
            continue
        try:
            content = f.file.read()
            text = extract_text_from_bytes(content, f.filename)
            if not text.strip():
                errors.append(f"{f.filename}: file is empty")
                continue
            if do_anonymize:
                text = anonymize_text(text, settings)
            title = f.filename.rsplit(".", 1)[0] if "." in f.filename else f.filename
            metadata = {"anonymized": True} if do_anonymize else None
            items.append({"text": text, "title": title, "metadata": metadata, "group": group})
            if upload_dir and (name.endswith(".pdf") or name.endswith(".docx")):
                file_data.append((content, f.filename))
            else:
                file_data.append((None, ""))  # one entry per item so index matches
        except Exception as e:
            errors.append(f"{f.filename}: {e}")

    if not items:
        raise HTTPException(
            status_code=400,
            detail=errors[0] if errors else "No valid .txt, .docx, or .pdf files provided",
        )
    ids = add_snippets(items)

    if upload_dir:
        upload_dir.mkdir(parents=True, exist_ok=True)
        for i, (snippet_id, (content, filename)) in enumerate(zip(ids, file_data)):
            if content is None or not filename:
                continue
            try:
                snippet_upload = upload_dir / snippet_id
                snippet_upload.mkdir(parents=True, exist_ok=True)
                safe_name = _sanitize_filename(filename)
                out_path = snippet_upload / safe_name
                out_path.write_bytes(content)
                url = f"/api/snippets/{snippet_id}/document"
                item = items[i]
                update_snippet(
                    snippet_id,
                    item["text"],
                    item.get("title"),
                    metadata={"source_document_url": url},
                    group=item.get("group"),
                )
                meta = get_snippet_metadata(snippet_id)
                if not (meta and meta.get("source_document_url")):
                    logging.warning(
                        "Upload: source_document_url not persisted for snippet %s",
                        snippet_id,
                    )
            except Exception:
                pass  # keep snippet; link not set

    return {"ids": ids, "count": len(ids), "errors": errors if errors else None}


@app.get("/api/users", response_model=list[UserResponse])
def get_users(
    current_user: Annotated[dict, Depends(get_current_admin)] = None,
):
    """List all users (admin only)."""
    users = list_users()
    return [
        UserResponse(
            id=u["id"],
            email=u["email"],
            role=u["role"],
            status=u.get("status", "active"),
            created_at=u.get("created_at"),
        )
        for u in users
    ]


@app.post("/api/users", response_model=UserResponse)
def create_user_admin(
    payload: UserCreateAdmin,
    current_user: Annotated[dict, Depends(get_current_admin)] = None,
):
    """Create a user (admin only)."""
    if payload.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="role must be 'user' or 'admin'")
    email = payload.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Invalid email format")
    if get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = create_user(email, payload.password, role=payload.role, status="active")
    return UserResponse(
        id=user["id"],
        email=user["email"],
        role=user["role"],
        status=user.get("status", "active"),
        created_at=user.get("created_at"),
    )


@app.patch("/api/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    payload: UserUpdate,
    current_user: Annotated[dict, Depends(get_current_admin)] = None,
):
    """Update user status and/or role (admin only)."""
    if payload.status is None and payload.role is None:
        raise HTTPException(status_code=400, detail="Nothing to update")
    if payload.status is not None and payload.status not in ("active",):
        raise HTTPException(status_code=400, detail="status must be 'active'")
    if payload.role is not None and payload.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="role must be 'user' or 'admin'")
    target = get_user_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if payload.role is not None and payload.role != target["role"]:
        if target["role"] == "admin" and payload.role != "admin" and count_admins() <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last admin")
        set_user_role(user_id, payload.role)
    if payload.status is not None:
        set_user_status(user_id, payload.status)
    updated = get_user_by_id(user_id)
    return UserResponse(
        id=updated["id"],
        email=updated["email"],
        role=updated["role"],
        status=updated.get("status", "active"),
        created_at=updated.get("created_at"),
    )


@app.delete("/api/users/{user_id}")
def delete_user_endpoint(
    user_id: str,
    current_user: Annotated[dict, Depends(get_current_admin)] = None,
):
    """Delete a user (admin only). Forbidden if deleting the last admin."""
    target = get_user_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target["role"] == "admin" and count_admins() <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last admin")
    delete_user(user_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Admin: Prompt Management
# ---------------------------------------------------------------------------

@app.get("/api/admin/prompts", response_model=list[PromptItem])
def get_prompts(
    current_user: Annotated[dict, Depends(get_current_admin)],
):
    """List all prompt templates with current values and metadata (admin only)."""
    from .prompt_store import list_prompts
    return [PromptItem(**p) for p in list_prompts()]


@app.put("/api/admin/prompts/{key}", response_model=PromptItem)
def update_prompt(
    key: str,
    payload: PromptUpdate,
    current_user: Annotated[dict, Depends(get_current_admin)],
):
    """Update a prompt template (admin only)."""
    from .prompt_store import PROMPT_DEFAULTS, set_prompt, get_prompt as _get_prompt

    if key not in PROMPT_DEFAULTS:
        raise HTTPException(status_code=404, detail=f"Unknown prompt key: {key}")
    set_prompt(key, payload.template)
    defn = PROMPT_DEFAULTS[key]
    return PromptItem(
        key=key,
        label=defn.label,
        description=defn.description,
        placeholders=defn.placeholders,
        group=defn.group,
        template=payload.template,
        default_template=defn.default,
        is_default=False,
    )


@app.post("/api/admin/prompts/{key}/reset", response_model=PromptItem)
def reset_prompt(
    key: str,
    current_user: Annotated[dict, Depends(get_current_admin)],
):
    """Reset a prompt template to its default (admin only)."""
    from .prompt_store import PROMPT_DEFAULTS, reset_prompt as _reset_prompt

    if key not in PROMPT_DEFAULTS:
        raise HTTPException(status_code=404, detail=f"Unknown prompt key: {key}")
    _reset_prompt(key)
    defn = PROMPT_DEFAULTS[key]
    return PromptItem(
        key=key,
        label=defn.label,
        description=defn.description,
        placeholders=defn.placeholders,
        group=defn.group,
        template=defn.default,
        default_template=defn.default,
        is_default=True,
    )


# ---------------------------------------------------------------------------
# Admin: Backup & Restore
# ---------------------------------------------------------------------------

@app.get("/api/admin/backup")
def backup_data(
    current_user: Annotated[dict, Depends(get_current_admin)],
):
    """Download a .tar.gz snapshot of the entire data/ directory (admin only).

    Includes ChromaDB, SQLite user DB, and uploaded documents.
    """
    settings = get_settings()
    data_dir = Path(settings.chroma_persist_dir).parent
    if not data_dir.is_dir():
        raise HTTPException(status_code=404, detail="Data directory not found")

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(str(data_dir), arcname="data")
    buf.seek(0)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    filename = f"backup-{ts}.tar.gz"
    return StreamingResponse(
        buf,
        media_type="application/gzip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/api/admin/restore")
def restore_data(
    current_user: Annotated[dict, Depends(get_current_admin)],
    file: UploadFile = File(...),
):
    """Upload a .tar.gz backup to replace the data/ directory (admin only).

    After extraction the ChromaDB client is reconnected and the SQLite
    database is re-initialised.

    The archive should contain a top-level ``data/`` folder (as created by
    the backup endpoint or ``tar czf backup.tar.gz data``).
    """
    if not file.filename or not file.filename.endswith((".tar.gz", ".tgz")):
        raise HTTPException(status_code=400, detail="File must be a .tar.gz archive")

    settings = get_settings()
    data_dir = Path(settings.chroma_persist_dir).resolve().parent  # e.g. /app/data

    # Reset ChromaDB so it releases file handles before we overwrite
    from .store import reset_client
    reset_client()

    content = file.file.read()
    buf = io.BytesIO(content)

    try:
        with tarfile.open(fileobj=buf, mode="r:gz") as tar:
            # Security: reject absolute paths and path traversal
            for member in tar.getmembers():
                if member.name.startswith("/") or ".." in member.name:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unsafe path in archive: {member.name}",
                    )

            # Extract to a temp directory first, then move into place
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                tar.extractall(path=tmpdir)

                # Find the extracted data dir (could be "data" or just files)
                extracted = Path(tmpdir) / "data"
                if not extracted.is_dir():
                    # Fallback: maybe the tar root IS the data contents
                    extracted = Path(tmpdir)

                # Remove existing data and move extracted in
                if data_dir.is_dir():
                    shutil.rmtree(data_dir)
                shutil.copytree(str(extracted), str(data_dir))

    except tarfile.TarError as e:
        # Ensure data dir exists even if restore fails
        data_dir.mkdir(parents=True, exist_ok=True)
        raise HTTPException(status_code=400, detail=f"Invalid tar archive: {e}")
    except HTTPException:
        raise
    except Exception as e:
        data_dir.mkdir(parents=True, exist_ok=True)
        logging.exception("Restore failed")
        raise HTTPException(status_code=500, detail=f"Restore failed: {e}")

    # Re-initialise SQLite (creates tables if needed) and seed admin
    init_db()
    _seed_admin_if_needed()

    return {"ok": True, "message": "Data restored successfully. ChromaDB will reconnect on next request."}


# ---------------------------------------------------------------------------
# Admin: Collection Import / Export
# ---------------------------------------------------------------------------

_RUNTIME_METADATA_KEYS = frozenset({
    "has_generated_translations", "available_languages",
    "is_generated_translation", "translation_source",
})


def _clean_metadata_for_export(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Strip runtime-only computed fields from metadata for export."""
    if not metadata:
        return {}
    return {k: v for k, v in metadata.items() if k not in _RUNTIME_METADATA_KEYS}


@app.post("/api/admin/import-collection")
def import_collection(
    current_user: Annotated[dict, Depends(get_current_admin)],
    file: UploadFile = File(...),
):
    """Import a collection from a grouped JSON file (admin only).

    The file is a JSON array of grouped snippet objects.  Each object has a
    ``title``, ``group``, shared ``metadata``, and a ``translations`` dict
    keyed by language code containing ``text``, ``example_questions``, and
    ``is_generated_translation``.

    Existing snippets in the group(s) present in the file are **replaced**.
    """
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="File must be a .json file")

    try:
        content = file.file.read()
        raw = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    if not isinstance(raw, list):
        raise HTTPException(status_code=400, detail="JSON must be an array of snippet objects")

    try:
        entries = [CollectionGroupedItem(**item) for item in raw]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Validation error: {e}")

    if not entries:
        raise HTTPException(status_code=400, detail="No snippets in file")

    groups_in_file: set[str] = {e.group for e in entries}
    replaced_groups: list[str] = []
    for g in groups_in_file:
        count = delete_snippets_by_group(g)
        if count > 0:
            replaced_groups.append(g)

    from .store import _chunk_text, _get_collection, _index_example_questions
    from .embeddings import embed

    settings = get_settings()
    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap
    coll = _get_collection()

    total_originals = 0
    total_translations = 0

    for entry in entries:
        originals = {
            lang: tr for lang, tr in entry.translations.items()
            if not tr.is_generated_translation
        }
        generated = {
            lang: tr for lang, tr in entry.translations.items()
            if tr.is_generated_translation
        }

        if not originals:
            logger.warning("Skipping '%s': no original translations", entry.title)
            continue

        first_lang = next(iter(originals))
        first_tr = originals[first_lang]

        shared_meta = dict(entry.metadata) if entry.metadata else {}
        shared_meta["language"] = first_lang
        if first_tr.example_questions:
            shared_meta["example_questions"] = first_tr.example_questions

        # Build linked_snippets for backward compat with retrieval pipeline
        if len(originals) > 1:
            all_titles = [f"{entry.title}-{lang}" for lang in originals]
            shared_meta["linked_snippets"] = [
                t for t in all_titles if t != f"{entry.title}-{first_lang}"
            ]

        items = [{
            "text": first_tr.text,
            "title": entry.title,
            "metadata": shared_meta,
            "group": entry.group,
        }]
        ids = add_snippets(items, skip_translation=True)
        parent_id = ids[0]
        total_originals += 1

        if first_tr.example_questions:
            _index_example_questions(
                parent_id, first_tr.example_questions, entry.title, entry.group
            )

        remaining_originals = {
            lang: tr for lang, tr in originals.items() if lang != first_lang
        }
        all_extra: dict[str, TranslationEntry] = {**remaining_originals, **generated}

        for lang, tr in all_extra.items():
            tr_text = tr.text.strip()
            if not tr_text:
                continue

            is_gen = tr.is_generated_translation or lang in generated
            chunks = _chunk_text(tr_text, chunk_size, overlap)
            tr_ids: list[str] = []
            tr_docs: list[str] = []
            tr_metas: list[dict] = []
            for idx, chunk in enumerate(chunks):
                base_id = f"{parent_id}_tr_{lang}"
                doc_id = base_id if len(chunks) == 1 else f"{base_id}_{idx}"
                chunk_meta: dict[str, Any] = {
                    "title": entry.title,
                    "parent_id": parent_id,
                    "chunk_index": str(idx),
                    "group": entry.group,
                    "original_language": first_lang,
                    "translation_language": lang,
                    "is_translation": "true",
                }
                enriched: dict[str, Any] = dict(shared_meta)
                enriched["language"] = lang
                enriched.pop("linked_snippets", None)
                enriched.pop("example_questions", None)
                if tr.example_questions:
                    enriched["example_questions"] = tr.example_questions
                enriched["translation_source"] = "generated" if is_gen else "original"
                chunk_meta["metadata_json"] = json.dumps(enriched)
                tr_ids.append(doc_id)
                tr_docs.append(chunk)
                tr_metas.append(chunk_meta)

            if tr_ids:
                embeddings = embed(tr_docs).tolist()
                coll.add(ids=tr_ids, embeddings=embeddings, documents=tr_docs, metadatas=tr_metas)
                total_translations += 1

            if tr.example_questions:
                _index_example_questions(
                    f"{parent_id}_tr_{lang}", tr.example_questions, entry.title, entry.group
                )

    return {
        "imported": total_originals,
        "translation_entries": total_translations,
        "groups": sorted(groups_in_file),
        "replaced_groups": sorted(replaced_groups),
    }


@app.get("/api/admin/export-collection")
def export_collection(
    current_user: Annotated[dict, Depends(get_current_admin)],
    group: Annotated[list[str] | None, Query()] = None,
    language: Annotated[list[str] | None, Query()] = None,
):
    """Export snippets as a grouped JSON file (admin only).

    Returns a JSON array where each entry has ``title``, ``group``,
    shared ``metadata``, and a ``translations`` dict keyed by language
    code.
    """
    grouped_snippets, _ = list_snippets_grouped(
        limit=100_000, offset=0,
        group_names=group if group and len(group) > 0 else None,
        languages=language if language and len(language) > 0 else None,
    )

    output: list[dict[str, Any]] = []
    for s in grouped_snippets:
        clean_meta = _clean_metadata_for_export(s.get("metadata"))
        translations: dict[str, dict[str, Any]] = {}
        for lang, tr in (s.get("translations") or {}).items():
            tr_out: dict[str, Any] = {"text": tr["text"]}
            if tr.get("example_questions"):
                tr_out["example_questions"] = tr["example_questions"]
            if tr.get("is_generated_translation"):
                tr_out["is_generated_translation"] = True
            translations[lang] = tr_out

        output.append({
            "title": s.get("title") or "",
            "group": s.get("group") or "",
            "metadata": clean_meta if clean_meta else None,
            "translations": translations,
        })

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    group_suffix = f"-{group[0]}" if group and len(group) == 1 else ""
    filename = f"collection{group_suffix}-{ts}.json"

    json_bytes = json.dumps(output, ensure_ascii=False, indent=2).encode("utf-8")
    buf = io.BytesIO(json_bytes)
    return StreamingResponse(
        buf,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/health")
def health():
    """Basic liveness check."""
    return {"status": "ok"}



@app.get("/health/ready")
def health_ready():
    """Readiness check: verifies ChromaDB and SQLite are accessible."""
    errors: list[str] = []
    # Check SQLite
    try:
        from .user_store import _get_connection
        conn = _get_connection()
        conn.execute("SELECT 1")
        conn.close()
    except Exception as e:
        errors.append(f"sqlite: {e}")
    # Check ChromaDB
    try:
        from .store import _get_collection
        coll = _get_collection()
        coll.count()
    except Exception as e:
        errors.append(f"chromadb: {e}")
    if errors:
        raise HTTPException(status_code=503, detail={"status": "unhealthy", "errors": errors})
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Serve built frontend (SPA) in production
# ---------------------------------------------------------------------------
_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

if _STATIC_DIR.is_dir():
    # Serve static assets (JS, CSS, images, etc.)
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="static-assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        """Serve the SPA index.html for any non-API route (client-side routing)."""
        file_path = _STATIC_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_STATIC_DIR / "index.html")
