"""ChromaDB store for snippets."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from .config import get_settings
from .embeddings import embed


def _get_chroma_path() -> Path:
    p = Path(get_settings().chroma_persist_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


_client: chromadb.PersistentClient | None = None
_collection_name = "snippets"


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=str(_get_chroma_path()),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def _get_collection():
    return _get_client().get_or_create_collection(
        _collection_name,
        metadata={"description": "Text snippets for RAG"},
    )


def add_snippets(items: list[dict]) -> list[str]:
    """Add snippets. Each item: {text, title?, metadata?}. Returns list of ids."""
    if not items:
        return []
    texts = [it["text"] for it in items]
    embeddings = embed(texts).tolist()
    ids = [str(uuid.uuid4()) for _ in items]
    metadatas = []
    for it in items:
        meta = {"title": it.get("title") or ""}
        if it.get("metadata"):
            meta["metadata_json"] = json.dumps(it["metadata"])
        metadatas.append(meta)
    coll = _get_collection()
    coll.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    return ids


def query_snippets(query_embedding: list[float], top_k: int = 5) -> list[dict]:
    """Return list of {id, text, title?, metadata?, distance}."""
    coll = _get_collection()
    n = coll.count()
    if n == 0:
        return []
    result = coll.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, n),
        include=["documents", "metadatas", "distances"],
    )
    ids = result["ids"][0]
    docs = result["documents"][0]
    metas = result["metadatas"][0]
    distances = result["distances"][0]
    out = []
    for i, id_ in enumerate(ids):
        meta = metas[i] or {}
        title = meta.get("title") or None
        md = meta.get("metadata_json")
        metadata = json.loads(md) if md else None
        out.append({
            "id": id_,
            "text": docs[i],
            "title": title,
            "metadata": metadata,
            "distance": float(distances[i]),
        })
    return out


def list_snippets(limit: int = 100, offset: int = 0) -> tuple[list[dict], int]:
    """Return (snippets, total). Snippets have id, text, title, metadata."""
    coll = _get_collection()
    total = coll.count()
    if total == 0:
        return [], 0
    result = coll.get(
        include=["documents", "metadatas"],
        limit=limit,
        offset=offset,
    )
    snippets = []
    for i, id_ in enumerate(result["ids"]):
        meta = (result["metadatas"] or [None] * len(result["ids"]))[i] or {}
        title = meta.get("title") or None
        md = meta.get("metadata_json")
        metadata = json.loads(md) if md else None
        snippets.append({
            "id": id_,
            "text": result["documents"][i],
            "title": title,
            "metadata": metadata,
        })
    return snippets, total
