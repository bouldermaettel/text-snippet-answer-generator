"""Retrieve snippets and compute confidence scores."""
from __future__ import annotations

from .embeddings import embed
from .store import query_snippets


def _distance_to_confidence(distance: float) -> float:
    """Chroma L2 distance: lower is better. Map to [0,1] confidence (1 = best)."""
    if distance <= 0:
        return 1.0
    # heuristic: distance often in [0, 2] for normalized embeddings; 2 -> ~0, 0 -> 1
    import math
    return max(0.0, min(1.0, 1.0 - (distance / 2.0)))


def retrieve_and_score(question: str, top_k: int = 5) -> list[dict]:
    """Return list of {id, text, title, metadata, snippet_confidence}."""
    q_emb = embed([question])[0].tolist()
    raw = query_snippets(q_emb, top_k=top_k)
    out = []
    for r in raw:
        conf = _distance_to_confidence(r["distance"])
        out.append({
            "id": r["id"],
            "text": r["text"],
            "title": r.get("title"),
            "metadata": r.get("metadata"),
            "snippet_confidence": round(conf, 4),
        })
    return out


def answer_confidence(snippet_confidences: list[float]) -> float:
    """Single score for the answer from snippet confidences."""
    if not snippet_confidences:
        return 0.0
    top = snippet_confidences[:3]
    return round(0.6 * max(top) + 0.4 * (sum(top) / len(top)), 4)
