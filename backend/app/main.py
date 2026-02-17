"""FastAPI app: /api/ask, /api/snippets, /api/auth, /api/users."""
import io
import logging
import os
import re
import shutil
import tarfile
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, File, Form, FastAPI, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .auth import authenticate_user, create_access_token, get_current_admin, get_current_user
from .config import get_settings
from .generation import generate_answer, refine_answer
from .models import (
    AskRequest,
    AskResponse,
    RefineRequest,
    RefineResponse,
    SourceItem,
    SnippetCreate,
    SnippetItem,
    SnippetListResponse,
    SnippetUpdate,
    ExampleQuestionsUpdate,
    TokenResponse,
    UserCreate,
    UserCreateAdmin,
    UserLogin,
    UserResponse,
    UserStatusUpdate,
)
from .retrieval import answer_confidence, retrieve_and_score
from .store import add_snippets, delete_snippet, get_linked_snippets, get_snippet_metadata, list_groups, list_snippets, update_example_questions, update_snippet
from .anonymize import anonymize_text
from .upload import extract_text_from_bytes
from .user_store import count_admins, create_user, delete_user, get_user_by_email, get_user_by_id, init_db, list_users, set_user_status


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


@app.get("/api/snippets", response_model=SnippetListResponse)
def get_snippets(
    limit: int = 100,
    offset: int = 0,
    group: Annotated[list[str] | None, Query()] = None,
    language: Annotated[list[str] | None, Query()] = None,
    include_translations: bool = False,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """List snippets (paginated). Optional filters: group(s), language(s), include_translations."""
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


@app.patch("/api/snippets/{snippet_id}")
def patch_snippet(
    snippet_id: str,
    payload: SnippetUpdate,
    current_user: Annotated[dict, Depends(get_current_user)] = None,
):
    """Update a snippet by id."""
    update_snippet(snippet_id, payload.text, payload.title, metadata=payload.metadata, group=payload.group)
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
def update_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    current_user: Annotated[dict, Depends(get_current_admin)] = None,
):
    """Set user status (admin only). Used to approve pending users."""
    if payload.status not in ("active",):
        raise HTTPException(status_code=400, detail="status must be 'active'")
    target = get_user_by_id(user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
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
