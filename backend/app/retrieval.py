"""Retrieve snippets and compute confidence scores."""
from __future__ import annotations

import logging
import re

from .config import get_settings
from .embeddings import embed
from .generation import generate_hypothetical_answer
from .store import query_snippets, query_example_questions

logger = logging.getLogger(__name__)


def _distance_to_confidence(distance: float) -> float:
    """Chroma L2 distance: lower is better. Map to [0,1] confidence (1 = best)."""
    if distance <= 0:
        return 1.0
    # heuristic: distance often in [0, 2] for normalized embeddings; 2 -> ~0, 0 -> 1
    return max(0.0, min(1.0, 1.0 - (distance / 2.0)))


def _keyword_score(question: str, snippet_text: str) -> float:
    """Score [0,1] by fraction of question tokens found in snippet (case-insensitive)."""
    if not question or not snippet_text:
        return 0.0
    tokens = set(re.findall(r"\w+", question.lower()))
    if not tokens:
        return 0.0
    snippet_lower = snippet_text.lower()
    hits = sum(1 for t in tokens if t in snippet_lower)
    return min(1.0, hits / len(tokens))


def _merge_snippet_and_example_results(
    snippet_results: list[dict],
    example_question_results: list[dict],
    top_k: int,
    eq_weight: float = 0.3,
) -> list[dict]:
    """Merge results from snippet search and example question search.
    
    Strategy:
    - Build a dict by snippet_id
    - For snippets found in both searches, boost the score
    - For snippets only in example questions, we need to fetch their full details
    - Rank by combined confidence score
    
    Args:
        snippet_results: Results from query_snippets (with id, text, title, metadata, distance)
        example_question_results: Results from query_example_questions (with snippet_id, distance)
        top_k: Number of results to return
        eq_weight: Weight for example question score (default 0.3)
    """
    by_snippet: dict[str, dict] = {}
    
    # Add snippet text search results
    for r in snippet_results:
        sid = r["id"]
        snippet_conf = _distance_to_confidence(r["distance"])
        by_snippet[sid] = {
            "id": sid,
            "text": r["text"],
            "title": r.get("title"),
            "metadata": r.get("metadata"),
            "distance": r["distance"],
            "snippet_conf": snippet_conf,
            "eq_conf": 0.0,
            "source": "snippet_text",
            "matched_question": None,
        }
    
    # Add/merge example question search results
    for eq in example_question_results:
        sid = eq["snippet_id"]
        eq_conf = _distance_to_confidence(eq["distance"])
        
        if sid in by_snippet:
            # Found in both - merge and mark as "both"
            by_snippet[sid]["eq_conf"] = max(by_snippet[sid]["eq_conf"], eq_conf)
            by_snippet[sid]["source"] = "both"
            if by_snippet[sid]["matched_question"] is None:
                by_snippet[sid]["matched_question"] = eq["question"]
        else:
            # Only in example questions - need to fetch snippet later
            by_snippet[sid] = {
                "id": sid,
                "text": None,  # Will be fetched
                "title": eq.get("title"),
                "metadata": None,
                "distance": eq["distance"],
                "snippet_conf": 0.0,
                "eq_conf": eq_conf,
                "source": "example_question",
                "matched_question": eq["question"],
            }
    
    # Calculate combined score: weighted combination
    # If found in both, we use weighted sum; if only one source, use that score
    snippet_weight = 1.0 - eq_weight
    for sid, r in by_snippet.items():
        if r["source"] == "both":
            # Boost for appearing in both searches
            r["combined_conf"] = snippet_weight * r["snippet_conf"] + eq_weight * r["eq_conf"]
        elif r["source"] == "snippet_text":
            r["combined_conf"] = r["snippet_conf"]
        else:  # example_question only
            r["combined_conf"] = r["eq_conf"]
    
    # Sort by combined confidence (descending) and take top_k
    sorted_results = sorted(by_snippet.values(), key=lambda x: x["combined_conf"], reverse=True)
    return sorted_results[:top_k]


def _fetch_missing_snippet_details(results: list[dict], languages: list[str] | None = None) -> list[dict]:
    """Fetch full snippet details for results that only came from example question search."""
    from .store import query_snippets
    
    # Find snippet IDs that need fetching (text is None)
    missing_ids = [r["id"] for r in results if r.get("text") is None]
    if not missing_ids:
        return results
    
    # Fetch by embedding a dummy query and filtering by IDs
    # This is a workaround - ideally we'd have a get_snippets_by_ids function
    # For now, use the existing infrastructure
    from .store import list_snippets
    
    # Fetch all snippets that match the missing IDs
    all_snippets, _ = list_snippets(limit=1000, languages=languages)
    snippet_map = {s["id"]: s for s in all_snippets if s["id"] in missing_ids}
    
    # Fill in missing details
    for r in results:
        if r.get("text") is None and r["id"] in snippet_map:
            s = snippet_map[r["id"]]
            r["text"] = s["text"]
            r["title"] = s.get("title") or r.get("title")
            r["metadata"] = s.get("metadata")
    
    # Remove any results where we couldn't fetch the snippet
    results = [r for r in results if r.get("text") is not None]
    
    return results


def retrieve_and_score(
    question: str,
    top_k: int = 5,
    group_names: list[str] | None = None,
    snippet_ids: list[str] | None = None,
    languages: list[str] | None = None,
    use_hyde: bool = False,
    use_keyword_rerank: bool = True,
    use_example_question_search: bool = True,
) -> list[dict]:
    """Return list of {id, text, title, metadata, snippet_confidence}.
    
    Hybrid retrieval with two search paths:
    1. Snippet text search: Uses HyDE (if enabled) to embed a hypothetical answer
    2. Example question search: Directly embeds user question to match against example questions
    
    Results from both paths are merged and ranked by combined confidence.
    
    Args:
        question: User's question
        top_k: Number of results to return
        group_names: Filter by groups
        snippet_ids: Filter by specific snippet IDs
        languages: Filter by languages
        use_hyde: Whether to use HyDE for snippet text search
        use_keyword_rerank: Whether to apply keyword-based reranking
        use_example_question_search: Whether to also search example questions (hybrid mode)
    """
    settings = get_settings()
    
    # Check if example question search is enabled
    enable_eq_search = (
        use_example_question_search 
        and getattr(settings, 'enable_example_question_search', True)
    )
    eq_weight = getattr(settings, 'example_question_search_weight', 0.3)
    
    # Path 1: Snippet text search (with HyDE if enabled)
    query_text = question
    if use_hyde and settings.hyde_enabled:
        hypothetical = generate_hypothetical_answer(question, settings)
        if hypothetical:
            query_text = hypothetical
            logger.debug("Using HyDE hypothetical answer for snippet search")
    
    hyde_emb = embed([query_text])[0].tolist()
    fetch_k = top_k * 2 if (use_keyword_rerank or enable_eq_search) else top_k
    
    snippet_results = query_snippets(
        hyde_emb,
        top_k=fetch_k,
        group_names=group_names,
        snippet_ids=snippet_ids,
        languages=languages,
    )
    
    # Path 2: Example question search (direct question embedding)
    example_question_results = []
    if enable_eq_search:
        # Embed the raw question (not the HyDE hypothetical)
        q_emb_direct = embed([question])[0].tolist()
        example_question_results = query_example_questions(
            q_emb_direct,
            top_k=fetch_k,
            group_names=group_names,
            snippet_ids=snippet_ids,
        )
        if example_question_results:
            logger.debug(
                "Found %d example question matches, top match: %s",
                len(example_question_results),
                example_question_results[0].get("question", "")[:50] if example_question_results else "",
            )
    
    # Merge results from both paths
    if enable_eq_search and example_question_results:
        merged = _merge_snippet_and_example_results(
            snippet_results, 
            example_question_results,
            top_k=fetch_k,
            eq_weight=eq_weight,
        )
        # Fetch details for snippets only found via example questions
        merged = _fetch_missing_snippet_details(merged, languages)
        raw = merged
    else:
        # No example question results, use snippet results directly
        raw = snippet_results
    
    # Apply keyword reranking if enabled
    if use_keyword_rerank and len(raw) > top_k:
        for r in raw:
            # Use combined_conf if available (from merge), else compute from distance
            base_conf = r.get("combined_conf") or _distance_to_confidence(r.get("distance", 0))
            kw = _keyword_score(question, r.get("text") or "")
            r["_combined"] = 0.7 * base_conf + 0.3 * kw
        raw = sorted(raw, key=lambda x: x["_combined"], reverse=True)[:top_k]
        for r in raw:
            r.pop("_combined", None)
    else:
        raw = raw[:top_k]
    
    # Build output
    out = []
    for r in raw:
        # Use combined_conf if available, else compute from distance
        conf = r.get("combined_conf") or _distance_to_confidence(r.get("distance", 0))
        result = {
            "id": r["id"],
            "text": r["text"],
            "title": r.get("title"),
            "metadata": r.get("metadata"),
            "snippet_confidence": round(conf, 4),
        }
        # Include source info for debugging/transparency
        if r.get("source"):
            result["retrieval_source"] = r["source"]
        if r.get("matched_question"):
            result["matched_example_question"] = r["matched_question"]
        out.append(result)
    
    return out


def answer_confidence(snippet_confidences: list[float]) -> float:
    """Single score for the answer from snippet confidences."""
    if not snippet_confidences:
        return 0.0
    top = snippet_confidences[:3]
    return round(0.6 * max(top) + 0.4 * (sum(top) / len(top)), 4)
