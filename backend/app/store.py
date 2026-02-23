"""ChromaDB store for snippets with chunking, groups, and translation indexing."""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from .config import get_settings
from .embeddings import embed

logger = logging.getLogger(__name__)


def _get_chroma_path() -> Path:
    p = Path(get_settings().chroma_persist_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


_client: chromadb.PersistentClient | None = None
_collection_name = "snippets"
_example_questions_collection_name = "example_questions"


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=str(_get_chroma_path()),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def reset_client() -> None:
    """Reset the ChromaDB client singleton so it reconnects on next access.

    Call this after restoring data from a backup so the client picks up
    the new database files.
    """
    global _client
    _client = None


def _get_collection():
    return _get_client().get_or_create_collection(
        _collection_name,
        metadata={"description": "Text snippets for RAG"},
    )


def _get_example_questions_collection():
    """Get or create the example questions collection for hybrid search."""
    return _get_client().get_or_create_collection(
        _example_questions_collection_name,
        metadata={"description": "Example questions linked to snippets for hybrid retrieval"},
    )


def _index_example_questions(
    snippet_id: str,
    example_questions: list[str],
    title: str = "",
    group: str = "",
) -> None:
    """Embed and store example questions for a snippet in the example_questions collection.
    
    Args:
        snippet_id: The parent snippet ID
        example_questions: List of example question strings
        title: Snippet title (for metadata)
        group: Snippet group (for filtering)
    """
    if not example_questions:
        return
    
    # Filter out empty questions
    questions = [q.strip() for q in example_questions if q and q.strip()]
    if not questions:
        return
    
    eq_coll = _get_example_questions_collection()
    
    # Generate IDs and metadata for each question
    eq_ids = [f"{snippet_id}_eq_{i}" for i in range(len(questions))]
    eq_metadatas = [
        {
            "snippet_id": snippet_id,
            "question_index": str(i),
            "title": title,
            "group": group,
        }
        for i in range(len(questions))
    ]
    
    # Embed all questions
    eq_embeddings = embed(questions).tolist()
    
    # Store in collection
    eq_coll.upsert(
        ids=eq_ids,
        embeddings=eq_embeddings,
        documents=questions,
        metadatas=eq_metadatas,
    )
    logger.info("Indexed %d example questions for snippet %s", len(questions), snippet_id)


def _delete_example_questions(snippet_id: str) -> None:
    """Delete all example questions associated with a snippet."""
    eq_coll = _get_example_questions_collection()
    eq_result = eq_coll.get(where={"snippet_id": snippet_id}, include=[])
    if eq_result["ids"]:
        eq_coll.delete(ids=eq_result["ids"])
        logger.info("Deleted %d example questions for snippet %s", len(eq_result["ids"]), snippet_id)


def _parse_metadata_json(md) -> dict | None:
    """Parse metadata_json from Chroma metadata; return None on missing or invalid."""
    if md is None:
        return None
    s = md if isinstance(md, str) else str(md)
    if not s.strip():
        return None
    try:
        out = json.loads(s)
        return out if isinstance(out, dict) else None
    except (TypeError, ValueError):
        return None


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks."""
    if not text or chunk_size <= 0:
        return [text] if text else []
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def _extract_languages_from_linked_snippets(linked_snippets: list[str]) -> set[str]:
    """Extract language codes from linked snippet titles.
    
    Expects titles like "Actors-de", "Actors-en", "Actors-fr", "Actors-it".
    Returns set of language codes found (e.g., {"de", "en", "fr", "it"}).
    """
    languages = set()
    for title in linked_snippets:
        if not title:
            continue
        # Check for language suffix like "-de", "-en", "-fr", "-it"
        for lang in ["de", "en", "fr", "it", "es", "pt", "nl", "pl", "ru", "zh", "ja", "ko"]:
            if title.lower().endswith(f"-{lang}"):
                languages.add(lang)
                break
    return languages


def add_snippets(items: list[dict], skip_translation: bool = False) -> list[str]:
    """Add snippets with optional translation indexing.
    
    Each item: {text, title?, metadata?, group?}.
    Returns list of logical snippet ids (parent_id).
    
    Translation indexing behavior:
    - If metadata contains 'linked_snippets', we check which languages are covered
    - LLM translations are only generated for MISSING target languages
    - Otherwise, if translation indexing is enabled, each snippet is translated
      to configured languages and stored as additional indexed documents
    """
    if not items:
        return []
    settings = get_settings()
    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap
    target_languages = set(settings.get_translation_languages())

    # Check if translation is enabled
    enable_translation = (
        not skip_translation
        and settings.enable_translation_indexing
    )
    
    # Lazy import to avoid circular imports
    if enable_translation:
        from .translation import detect_language, get_translations, is_translation_enabled
        enable_translation = is_translation_enabled(settings)

    all_ids: list[str] = []
    all_docs: list[str] = []
    all_metadatas: list[dict] = []
    parent_ids_ordered: list[str] = []

    # Track which linked groups already have translations being generated in this batch.
    # Key: frozenset of all titles in the linked group (including self).
    # Value: set of language codes that are already covered or being generated.
    linked_group_covered: dict[frozenset, set[str]] = {}

    for it in items:
        text = (it.get("text") or "").strip()
        if not text:
            continue
        title = it.get("title") or ""
        group = it.get("group") or ""
        metadata = it.get("metadata") or {}
        parent_id = str(uuid.uuid4())
        parent_ids_ordered.append(parent_id)

        covered_languages: set[str] = set()
        
        # Detect language from metadata or text
        original_language = metadata.get("language", "")
        if not original_language and enable_translation:
            original_language = detect_language(text, settings)
            logger.info("Detected language '%s' for snippet %s", original_language, parent_id)
        elif not original_language:
            original_language = "en"  # default
        
        # Add the snippet's own language to covered languages
        covered_languages.add(original_language)
        
        # linked_snippets are separate entries that already cover certain languages.
        # Extract those language codes so we don't generate redundant translations.
        linked_snippets = metadata.get("linked_snippets", [])
        group_key: frozenset | None = None
        if linked_snippets:
            linked_langs = _extract_languages_from_linked_snippets(linked_snippets)
            covered_languages.update(linked_langs)
            # Build a group key that includes this snippet's title + all linked titles
            all_titles = frozenset([title] + list(linked_snippets)) if title else None
            if all_titles:
                group_key = all_titles
                # Also include languages already being generated by siblings in this batch
                already_generating = linked_group_covered.get(group_key, set())
                covered_languages.update(already_generating)

        # Prepare text variants: original + translations for MISSING languages only
        text_variants: list[tuple[str, str, bool, str]] = [
            (text, original_language, False, "original")
        ]  # (text, lang, is_translation, translation_source)
        
        # Determine which languages need LLM translation
        missing_languages = target_languages - covered_languages
        
        if enable_translation and missing_languages:
            # Generate LLM translations only for missing languages
            logger.info(
                "Snippet %s: covered=%s, missing=%s, will generate translations for missing",
                parent_id, covered_languages, missing_languages,
            )
            translations = get_translations(text, original_language, settings=settings)
            for lang, translated_text in translations.items():
                if lang in missing_languages and translated_text:
                    text_variants.append((translated_text, lang, True, "generated"))
                    logger.info("Added %s translation (LLM-generated) for snippet %s", lang, parent_id)
        elif linked_snippets and not missing_languages:
            logger.info(
                "Snippet %s has all target languages covered (linked + batch): %s",
                parent_id, covered_languages,
            )
        
        # Record which languages this snippet covers for its linked group,
        # so sibling snippets in the same batch won't duplicate translations.
        if group_key is not None:
            generated_langs = {lang for _, lang, is_tr, _ in text_variants if is_tr}
            existing = linked_group_covered.get(group_key, set())
            linked_group_covered[group_key] = existing | covered_languages | generated_langs

        # Process each text variant (original + translations)
        for variant_text, variant_lang, is_translation, translation_source in text_variants:
            chunks = _chunk_text(variant_text, chunk_size, overlap)
            for idx, chunk in enumerate(chunks):
                # Create unique ID for each chunk, including language suffix for translations
                if is_translation:
                    base_id = f"{parent_id}_tr_{variant_lang}"
                    doc_id = base_id if len(chunks) == 1 else f"{base_id}_{idx}"
                else:
                    doc_id = parent_id if len(chunks) == 1 else f"{parent_id}_{idx}"
                
                # Build metadata
                meta = {
                    "title": title,
                    "parent_id": parent_id,
                    "chunk_index": str(idx),
                    "group": group,
                    "original_language": original_language,
                    "translation_language": variant_lang,
                    "is_translation": "true" if is_translation else "false",
                }
                
                # Merge user metadata with language info and translation source
                enriched_metadata = {
                    **metadata,
                    "language": variant_lang,
                    "translation_source": translation_source,  # "original", "existing", or "generated"
                }
                meta["metadata_json"] = json.dumps(enriched_metadata)
                
                all_ids.append(doc_id)
                all_docs.append(chunk)
                all_metadatas.append(meta)

    if not all_ids:
        return []

    all_embeddings = embed(all_docs).tolist()

    coll = _get_collection()
    coll.add(ids=all_ids, embeddings=all_embeddings, documents=all_docs, metadatas=all_metadatas)
    
    # Index example questions for each snippet (for hybrid search)
    for it, parent_id in zip(items, parent_ids_ordered):
        metadata = it.get("metadata") or {}
        example_questions = metadata.get("example_questions", [])
        if example_questions:
            title = it.get("title") or ""
            group = it.get("group") or ""
            _index_example_questions(parent_id, example_questions, title, group)
    
    return parent_ids_ordered


def _expand_chunks_to_parents(
    coll, raw_results: list[dict],
    target_language: str | None = None,
) -> list[dict]:
    """Given raw chunk results, group by parent_id and return one row per parent with merged text.
    
    Args:
        coll: ChromaDB collection
        raw_results: List of raw query results
        target_language: If set, return text in this language (original or translation).
                        If None, return original text.
    
    Includes translation info (has_generated_translations, available_languages) in metadata.
    """
    if not raw_results:
        return []
    parent_ids = list({r.get("parent_id") or r["id"] for r in raw_results})
    # Fetch all chunks for these parents (metadata has parent_id)
    all_chunks = coll.get(
        where={"parent_id": {"$in": parent_ids}},
        include=["documents", "metadatas"],
    )
    
    # Group chunks by parent_id and language
    # by_parent_lang[pid][lang] = list of (idx, doc, meta)
    by_parent_lang: dict[str, dict[str, list[tuple[int, str, dict]]]] = {}
    by_parent_original: dict[str, list[tuple[int, str, dict]]] = {}
    translations_by_parent: dict[str, set[str]] = {}  # parent_id -> set of translation languages
    
    for i, doc_id in enumerate(all_chunks["ids"]):
        meta = (all_chunks["metadatas"] or [{}])[i] or {}
        doc = (all_chunks["documents"] or [""])[i] or ""
        pid = meta.get("parent_id") or doc_id
        idx = int(meta.get("chunk_index", 0))
        is_translation = meta.get("is_translation", "false") == "true"
        trans_lang = (meta.get("translation_language", "") or "").lower()
        
        # Group by language
        if trans_lang:
            by_parent_lang.setdefault(pid, {}).setdefault(trans_lang, []).append((idx, doc, meta))
        
        if is_translation:
            # Track translation languages for this parent
            if trans_lang:
                translations_by_parent.setdefault(pid, set()).add(trans_lang)
        else:
            # Track original chunks
            by_parent_original.setdefault(pid, []).append((idx, doc, meta))
    
    # Backwards compat: old docs have no parent_id; fetch by id
    missing = [pid for pid in parent_ids if pid not in by_parent_lang]
    if missing:
        fallback = coll.get(ids=missing, include=["documents", "metadatas"])
        for i, doc_id in enumerate(fallback["ids"]):
            meta = (fallback["metadatas"] or [{}])[i] or {}
            doc = (fallback["documents"] or [""])[i] or ""
            trans_lang = (meta.get("translation_language", "") or "").lower() or "unknown"
            by_parent_lang.setdefault(doc_id, {}).setdefault(trans_lang, []).append((0, doc, meta))
            by_parent_original[doc_id] = [(0, doc, meta)]
    
    out = []
    target_lang_lower = target_language.lower() if target_language else None
    
    for pid in parent_ids:
        lang_chunks = by_parent_lang.get(pid, {})
        
        # Select chunks based on target language
        if target_lang_lower and target_lang_lower in lang_chunks:
            # Return text in target language
            chunks = lang_chunks[target_lang_lower]
        else:
            # Default: prefer original chunks
            chunks = by_parent_original.get(pid) or next(iter(lang_chunks.values()), None)
        
        if not chunks:
            continue
        
        chunks_sorted = sorted(chunks, key=lambda x: x[0])
        merged_text = "\n\n".join(c[1] for c in chunks_sorted)
        first_meta = chunks_sorted[0][2]
        title = first_meta.get("title") or None
        md = first_meta.get("metadata_json")
        metadata = _parse_metadata_json(md) or {}
        
        # Add translation info to metadata
        generated_langs = translations_by_parent.get(pid, set())
        linked_snippets = metadata.get("linked_snippets", [])
        original_lang = metadata.get("language", "")
        
        # Combine all available languages
        all_languages = set()
        if original_lang:
            all_languages.add(original_lang)
        all_languages.update(generated_langs)
        # Extract languages from linked_snippets titles
        all_languages.update(_extract_languages_from_linked_snippets(linked_snippets))
        
        metadata["has_generated_translations"] = len(generated_langs) > 0
        metadata["available_languages"] = sorted(all_languages)
        
        distances = [r["distance"] for r in raw_results if (r.get("parent_id") or r["id"]) == pid]
        best_dist = min(distances) if distances else 0.0
        out.append({
            "id": pid,
            "text": merged_text,
            "title": title,
            "metadata": metadata,
            "distance": best_dist,
        })
    out.sort(key=lambda x: x["distance"])
    return out


def query_snippets(
    query_embedding: list[float],
    top_k: int = 5,
    group_names: list[str] | None = None,
    snippet_ids: list[str] | None = None,
    languages: list[str] | None = None,
) -> list[dict]:
    """Return list of logical snippets {id (parent_id), text (merged), title?, metadata?, distance}.
    If group_names, snippet_ids, or languages set, filter by metadata. After retrieval, expand chunks to full parents.
    """
    coll = _get_collection()
    n = coll.count()
    if n == 0:
        return []

    # Build where clause for filtering
    conditions = []
    if group_names:
        conditions.append({"group": {"$in": group_names}})
    if snippet_ids:
        conditions.append({"parent_id": {"$in": snippet_ids}})
    if languages:
        # Filter by translation_language field (stored at Chroma metadata level)
        lang_lower = [lang.lower() for lang in languages]
        conditions.append({"translation_language": {"$in": lang_lower}})
    
    where = None
    if len(conditions) == 1:
        where = conditions[0]
    elif len(conditions) > 1:
        where = {"$and": conditions}

    fetch_n = min(top_k * 3, n)  # fetch more to allow expanding chunks
    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": fetch_n,
        "include": ["documents", "metadatas", "distances"],
    }
    if where is not None:
        kwargs["where"] = where

    result = coll.query(**kwargs)
    ids = result["ids"][0]
    docs = result["documents"][0]
    metas = result["metadatas"][0]
    distances = result["distances"][0]
    raw = []
    for i, id_ in enumerate(ids):
        meta = metas[i] or {}
        raw.append({
            "id": id_,
            "parent_id": meta.get("parent_id") or id_,
            "text": docs[i],
            "title": meta.get("title"),
            "metadata": _parse_metadata_json(meta.get("metadata_json")),
            "distance": float(distances[i]),
        })
    # Pass target language so we return text in the requested language
    target_lang = languages[0] if languages and len(languages) == 1 else None
    expanded = _expand_chunks_to_parents(coll, raw, target_language=target_lang)
    return expanded[:top_k]


def query_example_questions(
    query_embedding: list[float],
    top_k: int = 5,
    group_names: list[str] | None = None,
    snippet_ids: list[str] | None = None,
) -> list[dict]:
    """Search example questions collection for similar questions.
    
    Returns list of {snippet_id, question, distance, title, group}.
    Used for hybrid retrieval - matching user questions against example questions.
    """
    eq_coll = _get_example_questions_collection()
    n = eq_coll.count()
    if n == 0:
        return []
    
    # Build where clause for filtering
    conditions = []
    if group_names:
        conditions.append({"group": {"$in": group_names}})
    if snippet_ids:
        conditions.append({"snippet_id": {"$in": snippet_ids}})
    
    where = None
    if len(conditions) == 1:
        where = conditions[0]
    elif len(conditions) > 1:
        where = {"$and": conditions}
    
    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": min(top_k, n),
        "include": ["documents", "metadatas", "distances"],
    }
    if where is not None:
        kwargs["where"] = where
    
    result = eq_coll.query(**kwargs)
    
    if not result["ids"] or not result["ids"][0]:
        return []
    
    ids = result["ids"][0]
    docs = result["documents"][0]
    metas = result["metadatas"][0]
    distances = result["distances"][0]
    
    out = []
    for i, id_ in enumerate(ids):
        meta = metas[i] or {}
        out.append({
            "id": id_,
            "snippet_id": meta.get("snippet_id", ""),
            "question": docs[i],
            "title": meta.get("title", ""),
            "group": meta.get("group", ""),
            "distance": float(distances[i]),
        })
    
    return out


def list_snippets(
    limit: int = 100,
    offset: int = 0,
    group_name: str | None = None,
    group_names: list[str] | None = None,
    languages: list[str] | None = None,
    include_translations: bool = False,
) -> tuple[list[dict], int]:
    """Return (snippets, total). Optional filters by group, language, and translation status.
    
    Args:
        limit: Max snippets to return
        offset: Pagination offset
        group_name: Filter by single group
        group_names: Filter by multiple groups
        languages: Filter by language codes (e.g., ["de", "en"])
        include_translations: If True, include generated translations as separate entries
    
    Returns:
        Tuple of (snippets list, total count)
    """
    coll = _get_collection()
    n = coll.count()
    if n == 0:
        return [], 0
    fetch_limit = min(max(n, 10000), 500_000)
    result = coll.get(
        include=["documents", "metadatas"],
        limit=fetch_limit,
    )
    ids = result["ids"] or []
    if not ids:
        return [], 0
    
    # Normalize language filter
    lang_filter = {lang.lower() for lang in languages} if languages else None
    
    # Group by parent_id, tracking originals and translations separately
    by_parent: dict[str, list[tuple[int, str, dict]]] = {}
    translations_by_parent: dict[str, dict[str, list[tuple[int, str, dict]]]] = {}  # parent_id -> {lang -> chunks}
    
    for i, doc_id in enumerate(ids):
        meta = (result["metadatas"] or [{}])[i] or {}
        doc = (result["documents"] or [""])[i] or ""
        pid = meta.get("parent_id") or doc_id
        idx = int(meta.get("chunk_index", 0))
        is_translation = meta.get("is_translation", "false") == "true"
        trans_lang = meta.get("translation_language", "")
        
        if is_translation:
            # Track translation chunks by language
            if trans_lang:
                translations_by_parent.setdefault(pid, {}).setdefault(trans_lang, []).append((idx, doc, meta))
            continue
            
        by_parent.setdefault(pid, []).append((idx, doc, meta))
    
    snippets = []
    eq_coll = _get_example_questions_collection()
    
    # Process original snippets
    for pid, chunks in by_parent.items():
        chunks_sorted = sorted(chunks, key=lambda x: x[0])
        merged = "\n\n".join(c[1] for c in chunks_sorted)
        first = chunks_sorted[0][2]
        title = first.get("title") or None
        group = first.get("group") or ""  # "" = ungrouped
        metadata = _parse_metadata_json(first.get("metadata_json")) or {}
        
        # Add translation info to metadata
        generated_langs = set(translations_by_parent.get(pid, {}).keys())
        linked_snippets = metadata.get("linked_snippets", [])
        original_lang = metadata.get("language", "")
        
        # Combine available languages from own language, generated translations, and linked siblings
        all_languages = set()
        if original_lang:
            all_languages.add(original_lang)
        all_languages.update(generated_langs)
        all_languages.update(_extract_languages_from_linked_snippets(linked_snippets))
        
        metadata["has_generated_translations"] = len(generated_langs) > 0
        metadata["available_languages"] = sorted(all_languages)
        metadata["is_generated_translation"] = False
        
        # Fetch example questions from collection if not in metadata
        if "example_questions" not in metadata or not metadata["example_questions"]:
            eq_result = eq_coll.get(where={"snippet_id": pid}, include=["documents"])
            if eq_result["ids"]:
                metadata["example_questions"] = eq_result["documents"]
        
        # Apply language filter for original snippets
        snippet_lang = (original_lang or "").lower()
        if lang_filter and snippet_lang and snippet_lang not in lang_filter:
            continue
        
        snippets.append({
            "id": pid,
            "text": merged,
            "title": title,
            "group": group,
            "metadata": metadata,
        })
    
    # Include generated translations as separate entries if requested
    if include_translations:
        for pid, lang_chunks in translations_by_parent.items():
            # Get original snippet info for reference
            orig_chunks = by_parent.get(pid, [])
            orig_first = orig_chunks[0][2] if orig_chunks else {}
            orig_title = orig_first.get("title") or ""
            orig_group = orig_first.get("group") or ""
            
            for lang, chunks in lang_chunks.items():
                # Apply language filter
                if lang_filter and lang.lower() not in lang_filter:
                    continue
                
                chunks_sorted = sorted(chunks, key=lambda x: x[0])
                merged = "\n\n".join(c[1] for c in chunks_sorted)
                first = chunks_sorted[0][2]
                metadata = _parse_metadata_json(first.get("metadata_json")) or {}
                
                # Mark as generated translation
                metadata["is_generated_translation"] = True
                metadata["translation_source"] = "generated"
                metadata["has_generated_translations"] = False
                metadata["available_languages"] = [lang]
                
                # Fetch example questions for this translation from the collection
                translation_id = f"{pid}_tr_{lang}"
                eq_result = eq_coll.get(where={"snippet_id": translation_id}, include=["documents"])
                if eq_result["ids"]:
                    metadata["example_questions"] = eq_result["documents"]
                
                snippets.append({
                    "id": translation_id,
                    "text": merged,
                    "title": f"{orig_title} [{lang.upper()}]" if orig_title else f"[{lang.upper()}]",
                    "group": orig_group,
                    "metadata": metadata,
                })
    
    # Filter by group(s)
    if group_names is not None and len(group_names) > 0:
        want_set = {g if g else "" for g in group_names}
        snippets = [s for s in snippets if (s.get("group") or "") in want_set]
    elif group_name is not None:
        want = group_name if group_name else ""
        snippets = [s for s in snippets if (s.get("group") or "") == want]
    
    total = len(snippets)
    snippets = snippets[offset : offset + limit]
    return snippets, total


_RUNTIME_METADATA_KEYS = frozenset({
    "has_generated_translations",
    "available_languages",
    "is_generated_translation",
    "translation_source",
})


def _strip_lang_suffix(title: str) -> str:
    """Strip trailing language suffix (e.g. '-de', '-en') from a title."""
    for lang in ["de", "en", "fr", "it", "es", "pt", "nl", "pl", "ru", "zh", "ja", "ko"]:
        if title.lower().endswith(f"-{lang}"):
            return title[: -len(lang) - 1]
    return title


def list_snippets_grouped(
    limit: int = 100,
    offset: int = 0,
    group_name: str | None = None,
    group_names: list[str] | None = None,
    languages: list[str] | None = None,
) -> tuple[list[dict], int]:
    """Return snippets in grouped format with translations nested under each parent.

    Each returned dict has:
        id, title, group, metadata (shared),
        translations: {lang_code: {text, example_questions, is_generated_translation}}

    Groups entries that share the same ``parent_id`` (new import format) **or**
    are linked via the ``linked_snippets`` metadata field (old flat format).

    The language filter keeps groups that have *any* matching language variant.
    """
    coll = _get_collection()
    n = coll.count()
    if n == 0:
        return [], 0
    fetch_limit = min(max(n, 10000), 500_000)
    result = coll.get(include=["documents", "metadatas"], limit=fetch_limit)
    ids = result["ids"] or []
    if not ids:
        return [], 0

    lang_filter = {lang.lower() for lang in languages} if languages else None

    # Phase 1: group raw chunks by parent_id
    by_parent: dict[str, list[tuple[int, str, dict]]] = {}
    translations_by_parent: dict[str, dict[str, list[tuple[int, str, dict]]]] = {}

    for i, doc_id in enumerate(ids):
        meta = (result["metadatas"] or [{}])[i] or {}
        doc = (result["documents"] or [""])[i] or ""
        pid = meta.get("parent_id") or doc_id
        idx = int(meta.get("chunk_index", 0))
        is_translation = meta.get("is_translation", "false") == "true"
        trans_lang = meta.get("translation_language", "")

        if is_translation:
            if trans_lang:
                translations_by_parent.setdefault(pid, {}).setdefault(trans_lang, []).append(
                    (idx, doc, meta)
                )
            continue
        by_parent.setdefault(pid, []).append((idx, doc, meta))

    eq_coll = _get_example_questions_collection()

    # Phase 2: build per-parent snippet dicts
    parent_snippets: dict[str, dict] = {}
    title_to_pid: dict[str, str] = {}

    for pid, chunks in by_parent.items():
        chunks_sorted = sorted(chunks, key=lambda x: x[0])
        first = chunks_sorted[0][2]
        title = first.get("title") or ""
        grp = first.get("group") or ""
        metadata = _parse_metadata_json(first.get("metadata_json")) or {}

        original_lang = (metadata.get("language") or "").lower()
        original_text = "\n\n".join(c[1] for c in chunks_sorted)

        shared_meta: dict = {}
        for k, v in metadata.items():
            if k in ("language", "linked_snippets", "example_questions") or k in _RUNTIME_METADATA_KEYS:
                continue
            shared_meta[k] = v

        translations: dict[str, dict] = {}

        orig_eq = metadata.get("example_questions", [])
        if not orig_eq:
            eq_result = eq_coll.get(where={"snippet_id": pid}, include=["documents"])
            if eq_result["ids"]:
                orig_eq = eq_result["documents"]

        lang_key = original_lang or "unknown"
        translations[lang_key] = {
            "text": original_text,
            "example_questions": orig_eq if isinstance(orig_eq, list) else [],
            "is_generated_translation": False,
        }

        for lang, tr_chunks in translations_by_parent.get(pid, {}).items():
            tr_sorted = sorted(tr_chunks, key=lambda x: x[0])
            tr_text = "\n\n".join(c[1] for c in tr_sorted)
            tr_meta = _parse_metadata_json(tr_sorted[0][2].get("metadata_json")) or {}
            tr_eq = tr_meta.get("example_questions", [])
            if not tr_eq:
                translation_id = f"{pid}_tr_{lang}"
                eq_result = eq_coll.get(where={"snippet_id": translation_id}, include=["documents"])
                if eq_result["ids"]:
                    tr_eq = eq_result["documents"]
            is_gen = tr_meta.get("translation_source", "generated") == "generated"
            translations[lang] = {
                "text": tr_text,
                "example_questions": tr_eq if isinstance(tr_eq, list) else [],
                "is_generated_translation": is_gen,
            }

        parent_snippets[pid] = {
            "id": pid,
            "title": title or None,
            "group": grp,
            "metadata": shared_meta if shared_meta else None,
            "translations": translations,
            "_linked_snippets": metadata.get("linked_snippets", []),
        }
        if title:
            title_to_pid[title] = pid

    # Phase 3: merge entries linked via linked_snippets (old flat format)
    # Use union-find to group parent_ids that reference each other
    uf_parent: dict[str, str] = {}

    def uf_find(x: str) -> str:
        while uf_parent.get(x, x) != x:
            uf_parent[x] = uf_parent.get(uf_parent[x], uf_parent[x])
            x = uf_parent[x]
        return x

    def uf_union(a: str, b: str) -> None:
        ra, rb = uf_find(a), uf_find(b)
        if ra != rb:
            uf_parent[rb] = ra

    for pid, sn in parent_snippets.items():
        linked = sn.get("_linked_snippets", [])
        for linked_title in linked:
            linked_pid = title_to_pid.get(linked_title)
            if linked_pid and linked_pid != pid:
                uf_union(pid, linked_pid)

    # Group by union-find root
    merged_groups: dict[str, list[str]] = {}
    for pid in parent_snippets:
        root = uf_find(pid)
        merged_groups.setdefault(root, []).append(pid)

    # Phase 4: build final grouped output
    snippets: list[dict] = []
    for root, member_pids in merged_groups.items():
        if len(member_pids) == 1:
            sn = parent_snippets[member_pids[0]]
            sn.pop("_linked_snippets", None)
            if sn.get("title"):
                sn["title"] = _strip_lang_suffix(sn["title"])
            if lang_filter:
                if not any(lk in lang_filter for lk in sn["translations"]):
                    continue
            snippets.append(sn)
            continue

        # Merge multiple parent_ids into one grouped snippet
        primary = parent_snippets[root]
        merged_translations: dict[str, dict] = {}
        merged_meta: dict = dict(primary.get("metadata") or {})
        title = primary.get("title") or ""
        grp = primary.get("group") or ""

        for pid in member_pids:
            sn = parent_snippets[pid]
            for lang, tr in sn["translations"].items():
                if lang not in merged_translations:
                    merged_translations[lang] = tr
            # Fill shared metadata from any member that has it
            for k, v in (sn.get("metadata") or {}).items():
                if k not in merged_meta and v:
                    merged_meta[k] = v
            if not title and sn.get("title"):
                title = sn["title"]
            if not grp and sn.get("group"):
                grp = sn["group"]

        base_title = _strip_lang_suffix(title) if title else title

        if lang_filter:
            if not any(lk in lang_filter for lk in merged_translations):
                continue

        snippets.append({
            "id": root,
            "title": base_title or title or None,
            "group": grp,
            "metadata": merged_meta if merged_meta else None,
            "translations": merged_translations,
        })

    if group_names is not None and len(group_names) > 0:
        want_set = {g if g else "" for g in group_names}
        snippets = [s for s in snippets if (s.get("group") or "") in want_set]
    elif group_name is not None:
        want = group_name if group_name else ""
        snippets = [s for s in snippets if (s.get("group") or "") == want]

    total = len(snippets)
    snippets = snippets[offset : offset + limit]
    return snippets, total


def get_snippet_metadata(snippet_id: str) -> dict | None:
    """Return parsed metadata for a snippet (from first chunk), or None if not found."""
    coll = _get_collection()
    result = coll.get(
        where={"parent_id": snippet_id},
        include=["metadatas"],
        limit=1,
    )
    if not result["ids"]:
        result = coll.get(ids=[snippet_id], include=["metadatas"])
    if not result["ids"]:
        return None
    meta = (result["metadatas"] or [{}])[0] or {}
    return _parse_metadata_json(meta.get("metadata_json"))


def list_groups() -> list[str]:
    """Return distinct group names (including empty string for ungrouped)."""
    coll = _get_collection()
    n = coll.count()
    if n == 0:
        return []
    fetch_limit = min(max(n, 10000), 500_000)
    result = coll.get(include=["metadatas"], limit=fetch_limit)
    metas = result.get("metadatas") or []
    groups = set()
    for m in metas:
        if m and isinstance(m, dict):
            g = m.get("group")
            groups.add(g if g else "")
    return sorted(groups, key=lambda x: (x == "", x.lower()))


def update_snippet(
    snippet_id: str,
    text: str,
    title: str | None = None,
    metadata: dict | None = None,
    group: str | None = None,
    skip_translation: bool = False,
) -> bool:
    """Update a logical snippet (parent_id). Removes all its chunks (including translations) and re-adds.
    
    If translation indexing is enabled (and skip_translation=False), translations are regenerated
    only for languages not covered by linked_snippets.
    """
    coll = _get_collection()
    # Delete all existing chunks for this snippet (including translations)
    existing = coll.get(where={"parent_id": snippet_id}, include=[])
    if not existing["ids"]:
        # Old-format snippet: single doc with id = snippet_id (no parent_id in metadata)
        existing = coll.get(ids=[snippet_id], include=[])
    if existing["ids"]:
        coll.delete(ids=existing["ids"])
    
    # Delete old example questions
    _delete_example_questions(snippet_id)
    
    settings = get_settings()
    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap
    target_languages = set(settings.get_translation_languages())
    
    # Check if translation is enabled
    enable_translation = (
        not skip_translation
        and settings.enable_translation_indexing
    )
    
    if enable_translation:
        from .translation import detect_language, get_translations, is_translation_enabled
        enable_translation = is_translation_enabled(settings)

    text = text.strip()
    if not text:
        return True

    user_metadata = metadata or {}
    
    covered_languages: set[str] = set()

    # Detect language from metadata or text
    original_language = user_metadata.get("language", "")
    if not original_language and enable_translation:
        original_language = detect_language(text, settings)
        logger.info("Detected language '%s' for snippet %s (update)", original_language, snippet_id)
    elif not original_language:
        original_language = "en"  # default
    
    # Add the snippet's own language to covered languages
    covered_languages.add(original_language)
    
    # linked_snippets are separate entries that already cover certain languages.
    linked_snippets = user_metadata.get("linked_snippets", [])
    if linked_snippets:
        linked_langs = _extract_languages_from_linked_snippets(linked_snippets)
        covered_languages.update(linked_langs)

    # Prepare text variants: original + translations for MISSING languages only
    text_variants: list[tuple[str, str, bool]] = [(text, original_language, False)]
    
    # Determine which languages need LLM translation
    missing_languages = target_languages - covered_languages
    
    if enable_translation and missing_languages:
        logger.info(
            "Snippet %s (update): covered=%s, missing=%s, will generate translations",
            snippet_id, covered_languages, missing_languages,
        )
        translations = get_translations(text, original_language, settings=settings)
        for lang, translated_text in translations.items():
            if lang in missing_languages and translated_text:
                text_variants.append((translated_text, lang, True))
                logger.info("Added %s translation for snippet %s (update)", lang, snippet_id)

    ids = []
    docs = []
    metadatas_list = []
    user_metadata = metadata or {}

    # Process each text variant
    for variant_text, variant_lang, is_translation in text_variants:
        chunks = _chunk_text(variant_text, chunk_size, overlap)
        for idx, chunk in enumerate(chunks):
            if is_translation:
                base_id = f"{snippet_id}_tr_{variant_lang}"
                doc_id = base_id if len(chunks) == 1 else f"{base_id}_{idx}"
            else:
                doc_id = snippet_id if len(chunks) == 1 else f"{snippet_id}_{idx}"
            
            meta = {
                "title": title or "",
                "parent_id": snippet_id,
                "chunk_index": str(idx),
                "group": group or "",
                "original_language": original_language,
                "translation_language": variant_lang,
                "is_translation": "true" if is_translation else "false",
            }
            
            enriched_metadata = {**user_metadata, "language": variant_lang}
            meta["metadata_json"] = json.dumps(enriched_metadata)
            
            ids.append(doc_id)
            docs.append(chunk)
            metadatas_list.append(meta)

    if not ids:
        return True
        
    embeddings = embed(docs).tolist()
    coll.upsert(ids=ids, embeddings=embeddings, documents=docs, metadatas=metadatas_list)
    
    # Index example questions for hybrid search
    example_questions = user_metadata.get("example_questions", [])
    if example_questions:
        _index_example_questions(snippet_id, example_questions, title or "", group or "")
    
    return True


def update_snippet_grouped(
    snippet_id: str,
    title: str | None = None,
    group: str | None = None,
    metadata: dict | None = None,
    translations: dict[str, dict] | None = None,
) -> bool:
    """Update a snippet group: shared metadata + per-language texts.

    Removes all existing chunks/translations and re-indexes everything.
    ``translations`` is ``{lang: {text, example_questions, is_generated_translation}}``.
    """
    coll = _get_collection()

    existing = coll.get(where={"parent_id": snippet_id}, include=["metadatas"])
    if not existing["ids"]:
        existing = coll.get(ids=[snippet_id], include=["metadatas"])
    if not existing["ids"]:
        return False

    old_meta = (existing["metadatas"] or [{}])[0] or {}
    old_title = old_meta.get("title") or ""
    old_group = old_meta.get("group") or ""

    if title is None:
        title = old_title
    if group is None:
        group = old_group
    if translations is None:
        return True

    if existing["ids"]:
        coll.delete(ids=existing["ids"])
    _delete_example_questions(snippet_id)

    settings = get_settings()
    chunk_size = settings.chunk_size
    overlap = settings.chunk_overlap

    shared_meta = metadata or {}

    originals = {
        lang: tr for lang, tr in translations.items()
        if not tr.get("is_generated_translation", False)
    }
    generated = {
        lang: tr for lang, tr in translations.items()
        if tr.get("is_generated_translation", False)
    }

    if not originals:
        return True

    first_lang = next(iter(originals))
    first_tr = originals[first_lang]

    user_metadata = dict(shared_meta)
    user_metadata["language"] = first_lang
    if first_tr.get("example_questions"):
        user_metadata["example_questions"] = first_tr["example_questions"]

    all_ids: list[str] = []
    all_docs: list[str] = []
    all_metas: list[dict] = []

    first_text = first_tr["text"].strip()
    if first_text:
        chunks = _chunk_text(first_text, chunk_size, overlap)
        for idx, chunk in enumerate(chunks):
            doc_id = snippet_id if len(chunks) == 1 else f"{snippet_id}_{idx}"
            meta = {
                "title": title or "",
                "parent_id": snippet_id,
                "chunk_index": str(idx),
                "group": group or "",
                "original_language": first_lang,
                "translation_language": first_lang,
                "is_translation": "false",
            }
            meta["metadata_json"] = json.dumps({**user_metadata, "language": first_lang})
            all_ids.append(doc_id)
            all_docs.append(chunk)
            all_metas.append(meta)

    if first_tr.get("example_questions"):
        _index_example_questions(
            snippet_id, first_tr["example_questions"], title or "", group or ""
        )

    remaining: dict[str, dict] = {
        lang: tr for lang, tr in originals.items() if lang != first_lang
    }
    remaining.update(generated)

    for lang, tr in remaining.items():
        tr_text = tr["text"].strip()
        if not tr_text:
            continue
        chunks = _chunk_text(tr_text, chunk_size, overlap)
        for idx, chunk in enumerate(chunks):
            base_id = f"{snippet_id}_tr_{lang}"
            doc_id = base_id if len(chunks) == 1 else f"{base_id}_{idx}"
            meta = {
                "title": title or "",
                "parent_id": snippet_id,
                "chunk_index": str(idx),
                "group": group or "",
                "original_language": first_lang,
                "translation_language": lang,
                "is_translation": "true",
            }
            enriched = dict(shared_meta)
            enriched["language"] = lang
            if tr.get("example_questions"):
                enriched["example_questions"] = tr["example_questions"]
            enriched["translation_source"] = (
                "generated" if tr.get("is_generated_translation") else "original"
            )
            meta["metadata_json"] = json.dumps(enriched)
            all_ids.append(doc_id)
            all_docs.append(chunk)
            all_metas.append(meta)

        if tr.get("example_questions"):
            _index_example_questions(
                f"{snippet_id}_tr_{lang}", tr["example_questions"], title or "", group or ""
            )

    if all_ids:
        embeddings = embed(all_docs).tolist()
        coll.upsert(ids=all_ids, embeddings=embeddings, documents=all_docs, metadatas=all_metas)

    return True


def delete_snippet(snippet_id: str) -> bool:
    """Delete a logical snippet (all chunks with this parent_id) and its example questions."""
    coll = _get_collection()
    result = coll.get(where={"parent_id": snippet_id}, include=[])
    if result["ids"]:
        coll.delete(ids=result["ids"])
    
    # Delete associated example questions
    _delete_example_questions(snippet_id)
    
    return True


def delete_snippets_by_group(group_name: str) -> int:
    """Delete all snippets (and their example questions) belonging to a group.

    Returns the number of logical snippets deleted.
    """
    coll = _get_collection()
    n = coll.count()
    if n == 0:
        return 0

    fetch_limit = min(max(n, 10000), 500_000)
    result = coll.get(
        include=["metadatas"],
        limit=fetch_limit,
    )
    ids_to_delete: list[str] = []
    parent_ids: set[str] = set()

    target = group_name if group_name else ""
    for i, doc_id in enumerate(result["ids"]):
        meta = (result["metadatas"] or [{}])[i] or {}
        if (meta.get("group") or "") == target:
            ids_to_delete.append(doc_id)
            pid = meta.get("parent_id") or doc_id
            parent_ids.add(pid)

    if ids_to_delete:
        for batch_start in range(0, len(ids_to_delete), 5000):
            coll.delete(ids=ids_to_delete[batch_start : batch_start + 5000])

    eq_coll = _get_example_questions_collection()
    for pid in parent_ids:
        _delete_example_questions(pid)
        for lang in ("en", "de", "fr", "it", "es", "pt", "nl", "pl", "ru", "zh", "ja", "ko"):
            tr_id = f"{pid}_tr_{lang}"
            eq_result = eq_coll.get(where={"snippet_id": tr_id}, include=[])
            if eq_result["ids"]:
                eq_coll.delete(ids=eq_result["ids"])

    logger.info("Deleted %d chunks (%d logical snippets) from group '%s'",
                len(ids_to_delete), len(parent_ids), group_name)
    return len(parent_ids)


def update_example_questions(snippet_id: str, example_questions: list[str]) -> bool:
    """Update example questions for a snippet (original or translation).
    
    This re-indexes the questions in the example_questions collection.
    Works for both original snippets and auto-translations (IDs like xxx_tr_en).
    
    Args:
        snippet_id: The snippet ID (can be original or translation ID)
        example_questions: List of example question strings
    
    Returns:
        True if successful
    """
    # Get snippet info for metadata (title, group)
    # Try to get from existing example questions first
    eq_coll = _get_example_questions_collection()
    eq_result = eq_coll.get(where={"snippet_id": snippet_id}, include=["metadatas"], limit=1)
    
    title = ""
    group = ""
    
    if eq_result["ids"]:
        # Get title/group from existing example questions metadata
        meta = (eq_result["metadatas"] or [{}])[0] or {}
        title = meta.get("title", "")
        group = meta.get("group", "")
    else:
        # Try to get from snippets collection
        coll = _get_collection()
        # Check if it's a translation ID (contains _tr_)
        if "_tr_" in snippet_id:
            # Extract parent_id from translation ID
            parent_id = snippet_id.split("_tr_")[0]
            result = coll.get(where={"parent_id": parent_id}, include=["metadatas"], limit=1)
        else:
            result = coll.get(where={"parent_id": snippet_id}, include=["metadatas"], limit=1)
            if not result["ids"]:
                result = coll.get(ids=[snippet_id], include=["metadatas"])
        
        if result["ids"]:
            meta = (result["metadatas"] or [{}])[0] or {}
            title = meta.get("title", "")
            group = meta.get("group", "")
    
    # Delete old example questions
    _delete_example_questions(snippet_id)
    
    # Index new example questions if provided
    if example_questions:
        questions = [q.strip() for q in example_questions if q and q.strip()]
        if questions:
            _index_example_questions(snippet_id, questions, title, group)
            logger.info("Updated %d example questions for snippet %s", len(questions), snippet_id)
    
    return True


def get_snippets_by_titles(titles: list[str]) -> list[dict]:
    """Fetch snippets by their titles. Used for fetching linked translations.
    
    Returns list of {id, text, title, group, metadata} for each found snippet.
    """
    if not titles:
        return []
    
    coll = _get_collection()
    n = coll.count()
    if n == 0:
        return []
    
    # Fetch all snippets and filter by title (Chroma doesn't support $in on title)
    fetch_limit = min(max(n, 10000), 500_000)
    result = coll.get(
        include=["documents", "metadatas"],
        limit=fetch_limit,
    )
    ids = result["ids"] or []
    if not ids:
        return []
    
    # Normalize titles for matching (lowercase)
    title_set = {t.lower() for t in titles}
    
    # Group by parent_id, only including original chunks (not translations)
    by_parent: dict[str, list[tuple[int, str, dict]]] = {}
    for i, doc_id in enumerate(ids):
        meta = (result["metadatas"] or [{}])[i] or {}
        doc = (result["documents"] or [""])[i] or ""
        pid = meta.get("parent_id") or doc_id
        idx = int(meta.get("chunk_index", 0))
        is_translation = meta.get("is_translation", "false") == "true"
        title = (meta.get("title") or "").lower()
        
        # Skip translation chunks and non-matching titles
        if is_translation:
            continue
        if title not in title_set:
            continue
            
        by_parent.setdefault(pid, []).append((idx, doc, meta))
    
    snippets = []
    for pid, chunks in by_parent.items():
        chunks_sorted = sorted(chunks, key=lambda x: x[0])
        merged = "\n\n".join(c[1] for c in chunks_sorted)
        first = chunks_sorted[0][2]
        title = first.get("title") or None
        group = first.get("group") or ""
        metadata = _parse_metadata_json(first.get("metadata_json"))
        snippets.append({
            "id": pid,
            "text": merged,
            "title": title,
            "group": group,
            "metadata": metadata,
        })
    
    return snippets


def get_linked_snippets(snippet_id: str) -> list[dict]:
    """Get all linked translations for a snippet.
    
    Returns translations from TWO sources:
    1. linked_snippets metadata field (titles of related snippets)
    2. Generated translations (chunks with is_translation=true for this parent_id)
    
    Returns list of {id, text, title, group, metadata} including the original snippet.
    """
    coll = _get_collection()
    results = []
    seen_languages = set()
    
    # First get the original snippet's metadata and info
    original_meta = get_snippet_metadata(snippet_id)
    
    # Get the original snippet's title and text
    orig_result = coll.get(
        where={"parent_id": snippet_id},
        include=["metadatas", "documents"],
    )
    if not orig_result["ids"]:
        orig_result = coll.get(ids=[snippet_id], include=["metadatas", "documents"])
    
    original_title = None
    original_language = None
    
    # Build the original snippet from its chunks
    if orig_result["ids"]:
        by_type: dict[str, list[tuple[int, str, dict]]] = {"original": [], "translation": []}
        for i, doc_id in enumerate(orig_result["ids"]):
            meta = (orig_result["metadatas"] or [{}])[i] or {}
            doc = (orig_result["documents"] or [""])[i] or ""
            idx = int(meta.get("chunk_index", 0))
            is_translation = meta.get("is_translation", "false") == "true"
            
            if is_translation:
                by_type["translation"].append((idx, doc, meta))
            else:
                by_type["original"].append((idx, doc, meta))
                if not original_title:
                    original_title = meta.get("title")
        
        # Add the original snippet
        if by_type["original"]:
            chunks_sorted = sorted(by_type["original"], key=lambda x: x[0])
            merged = "\n\n".join(c[1] for c in chunks_sorted)
            first_meta = chunks_sorted[0][2]
            orig_md = _parse_metadata_json(first_meta.get("metadata_json")) or {}
            original_language = orig_md.get("language", "en")
            seen_languages.add(original_language)
            results.append({
                "id": snippet_id,
                "text": merged,
                "title": first_meta.get("title"),
                "group": first_meta.get("group", ""),
                "metadata": orig_md,
            })
        
        # Add generated translations (grouped by language)
        if by_type["translation"]:
            by_lang: dict[str, list[tuple[int, str, dict]]] = {}
            for idx, doc, meta in by_type["translation"]:
                lang = meta.get("translation_language", "")
                if lang:
                    by_lang.setdefault(lang, []).append((idx, doc, meta))
            
            for lang, chunks in by_lang.items():
                if lang in seen_languages:
                    continue
                seen_languages.add(lang)
                chunks_sorted = sorted(chunks, key=lambda x: x[0])
                merged = "\n\n".join(c[1] for c in chunks_sorted)
                first_meta = chunks_sorted[0][2]
                tr_md = _parse_metadata_json(first_meta.get("metadata_json")) or {}
                results.append({
                    "id": f"{snippet_id}_tr_{lang}",
                    "text": merged,
                    "title": f"{first_meta.get('title', '')} ({lang.upper()})",
                    "group": first_meta.get("group", ""),
                    "metadata": tr_md,
                })
    
    # Also fetch linked_snippets (other separate snippets)
    linked_titles = (original_meta or {}).get("linked_snippets", [])
    if linked_titles:
        if original_title and original_title not in linked_titles:
            linked_titles = list(linked_titles)  # Don't modify original
        
        linked_results = get_snippets_by_titles(linked_titles)
        for lr in linked_results:
            lr_lang = (lr.get("metadata") or {}).get("language", "")
            # Skip if we already have this language (from original or generated)
            if lr_lang in seen_languages:
                continue
            # Skip if this is the original snippet (already added)
            if lr.get("id") == snippet_id:
                continue
            seen_languages.add(lr_lang)
            results.append(lr)
    
    return results


def get_snippet_translation_info(snippet_id: str) -> dict:
    """Get info about available translations for a snippet.
    
    Returns {has_linked: bool, has_generated: bool, languages: list[str]}
    """
    coll = _get_collection()
    
    # Get all chunks for this snippet
    result = coll.get(
        where={"parent_id": snippet_id},
        include=["metadatas"],
    )
    if not result["ids"]:
        result = coll.get(ids=[snippet_id], include=["metadatas"])
    
    has_linked = False
    has_generated = False
    languages = set()
    
    for i, doc_id in enumerate(result.get("ids", [])):
        meta = (result["metadatas"] or [{}])[i] or {}
        is_translation = meta.get("is_translation", "false") == "true"
        lang = meta.get("translation_language", "")
        
        if is_translation:
            has_generated = True
        if lang:
            languages.add(lang)
        
        # Check for linked_snippets in metadata
        md = _parse_metadata_json(meta.get("metadata_json"))
        if md and md.get("linked_snippets"):
            has_linked = True
    
    return {
        "has_linked": has_linked,
        "has_generated": has_generated,
        "languages": sorted(languages),
    }
