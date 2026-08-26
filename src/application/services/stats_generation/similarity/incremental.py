"""
Similarity for a single tool, computed against the cached embedding corpus.

The full similarity run re-embeds every tool; that is too heavy to do when only
one record changed. This module embeds the one tool, compares it against the
vectors the full run cached, and writes just that tool's neighbour list -- plus,
optionally, a bounded reverse update so the new tool appears in the neighbour
lists of the tools it is most similar to (a full reconciliation still waits for
the next batch run).

The neighbour maths (`neighbours_for_vector`, `insert_into_neighbours`) are pure
and model-free so they can be tested with hand-built vectors; the model lives
behind the injected `embed_fn`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from application.services.stats_generation.similarity.compute_embeddings import (
    build_text,
)
from domain.repositories import Repositories

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def neighbours_for_vector(
    target_vec: np.ndarray,
    matrix: np.ndarray,
    ids: List[str],
    names: List[str],
    k: int,
    exclude_id: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], np.ndarray]:
    """
    Top-k neighbours of ``target_vec`` against ``matrix`` (rows aligned to ``ids``).

    Cosine similarity equals the dot product because both the target and the
    cached vectors are L2-normalised. Returns the neighbour list and the full
    score vector (the caller reuses the scores for the reverse update).
    """
    scores = matrix @ target_vec  # (N,)

    # argsort descending; skip the tool itself (its stale cached row is still in
    # the matrix) and any id equal to exclude_id.
    order = np.argsort(scores)[::-1]
    similar: List[Dict[str, Any]] = []
    for i in order:
        if exclude_id is not None and ids[i] == exclude_id:
            continue
        similar.append(
            {
                "tool_id": ids[i],
                "tool_name": names[i],
                "score": round(float(scores[i]), 4),
            }
        )
        if len(similar) >= k:
            break

    return similar, scores


def insert_into_neighbours(
    similar: List[Dict[str, Any]],
    target_id: str,
    target_name: str,
    target_score: float,
    k: int,
) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Fold one candidate into an existing neighbour list, trimmed to ``k``.

    Returns ``(new_list, changed)``. Any stale entry for ``target_id`` is dropped
    first, so re-running is idempotent: a tool whose score is unchanged produces
    the same list and ``changed=False``.
    """
    without_target = [s for s in similar if s.get("tool_id") != target_id]
    was_present = len(without_target) != len(similar)

    full = len(without_target) >= k
    min_score = without_target[-1]["score"] if full else float("-inf")

    if full and target_score <= min_score:
        # Not good enough to make the list. Only a change if we removed a stale
        # entry that had drifted out of the top-k.
        return (without_target[:k], was_present) if was_present else (similar, False)

    updated = without_target + [
        {"tool_id": target_id, "tool_name": target_name, "score": target_score}
    ]
    updated.sort(key=lambda s: s["score"], reverse=True)
    updated = updated[:k]

    changed = updated != similar
    return updated, changed


def compute_record_similarity(
    repos: Repositories,
    tool: Dict[str, Any],
    embed_fn: Callable[[str], np.ndarray],
    model_name: str,
    k: int = 12,
    reverse_update: bool = True,
    reverse_candidates: Optional[int] = None,
) -> Dict[str, int]:
    """
    Refresh one tool's similarity neighbours against the cached corpus.

    Parameters
    ----------
    embed_fn:
        ``text -> (dim,) float32 vector``. Injected so the model loads once at the
        edge and tests can pass a trivial embedder.
    model_name:
        The model ``embed_fn`` uses. Compared against the model the cache was built
        with; mixing vectors from different models is refused.
    reverse_update:
        When True, also insert this tool into the neighbour lists of the tools it
        is most similar to (bounded by ``reverse_candidates``).
    reverse_candidates:
        How many of the tool's own top neighbours to consider for the reverse
        update. Defaults to ``k``. Bounding it keeps the update to a handful of
        reads/writes rather than one per tool in the corpus.
    """
    tool_id = str(tool["_id"])
    data = tool.get("data", {})
    tool_name = data.get("name", "")
    text = build_text(data)

    ids, names, matrix, cache_model = repos.embeddings.load_all()

    if not ids:
        raise RuntimeError(
            "The embedding cache is empty. Run the full similarity stage once to "
            "populate it before enriching a single tool."
        )
    if cache_model and cache_model != model_name:
        raise ValueError(
            f"Embedding cache was built with model {cache_model!r} but this run "
            f"uses {model_name!r}; vectors from different models are not comparable. "
            "Re-run the full similarity stage with the desired model."
        )

    target_vec = np.asarray(embed_fn(text), dtype=np.float32)

    # Cache the fresh vector so future runs (and the next full run's diff) see it.
    repos.embeddings.upsert_by_tool_id(
        tool_id=tool_id,
        tool_name=tool_name,
        text=text,
        vector=target_vec.tolist(),
        model=model_name,
        version=tool.get("timestamp"),
    )

    similar, scores = neighbours_for_vector(
        target_vec, matrix, ids, names, k=k, exclude_id=tool_id
    )

    created_at = _utc_now_iso()
    repos.similarities.upsert_by_tool_id(
        {
            "tool_id": tool_id,
            "tool_name": tool_name,
            "similar": similar,
            "createdAt": created_at,
        }
    )

    result = {"neighbours": len(similar), "reverse_updated": 0}

    if not reverse_update:
        return result

    limit = reverse_candidates if reverse_candidates is not None else k
    order = np.argsort(scores)[::-1]
    considered = 0
    reverse_updated = 0
    for i in order:
        if ids[i] == tool_id:
            continue
        if considered >= limit:
            break
        considered += 1

        doc = repos.similarities.find_by_tool_id(ids[i])
        if doc is None:
            continue

        new_similar, changed = insert_into_neighbours(
            doc.get("similar", []),
            target_id=tool_id,
            target_name=tool_name,
            target_score=round(float(scores[i]), 4),
            k=k,
        )
        if not changed:
            continue

        # Rebuild the payload rather than write the fetched doc back: it carries an
        # `_id`, and `$set`-ing an immutable `_id` is rejected by MongoDB.
        repos.similarities.upsert_by_tool_id(
            {
                "tool_id": ids[i],
                "tool_name": doc.get("tool_name", names[i]),
                "similar": new_similar,
                "createdAt": created_at,
            }
        )
        reverse_updated += 1

    result["reverse_updated"] = reverse_updated
    return result
