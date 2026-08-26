"""
Use case: (re)generate all derived data for a single tool.

The batch stages compute FAIR scores, web availability and similarity across the
whole collection. This is their per-record counterpart: given one tool's ``_id``
it refreshes just that tool's FAIR score, probes its web pages, and recomputes
its similarity neighbours against the cached embedding corpus. It is the work
behind ``rsetl enrich-tool <id>``.

Each computation reuses the same service the batch path uses, so the per-record
and batch results stay consistent by construction.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Optional

import numpy as np

from application.services.stats_generation.similarity.incremental import (
    compute_record_similarity,
)
from application.use_cases.stats.generate_fair_scores import score_one_tool
from application.use_cases.web_availability.update_web_availability import (
    WebAvailabilityConfig,
    probe_tool_urls,
)
from domain.repositories import Repositories

logger = logging.getLogger(__name__)


def generate_record_data(
    repos: Repositories,
    tool_id: str,
    url_checker,
    make_embedder: Callable[[], Callable[[str], np.ndarray]],
    model_name: str,
    *,
    k: int = 12,
    force: bool = False,
    reverse_update: bool = True,
    reverse_candidates: Optional[int] = None,
    wa_config: Optional[WebAvailabilityConfig] = None,
) -> Dict[str, Any]:
    """
    Refresh FAIR scores, web availability and similarity for one tool.

    Parameters
    ----------
    make_embedder:
        A zero-arg factory returning a ``text -> vector`` callable. It is called
        only after the tool is found, so a bad id does not pay the (multi-second)
        cost of loading the embedding model.
    model_name:
        The model the embedder uses; must match the model the embedding cache was
        built with (the similarity service enforces this).
    force:
        Recompute the FAIR score even if the stored one is already up to date.
    reverse_update / reverse_candidates:
        Passed through to the similarity service -- whether, and how widely, to
        also insert this tool into other tools' neighbour lists.

    The three computations are independent: each runs and reports on its own, so a
    failure in one (most often similarity, when the embedding cache has not been
    populated yet) neither aborts the command nor discards the work the others
    already did. The returned ``ok`` flag is ``True`` only when all three
    succeeded; ``failed_stages`` names those that did not.
    """
    tool = repos.tools.find_by_id(tool_id)
    if tool is None:
        # The one hard error: with no tool there is nothing any stage can do.
        raise ValueError(f"No tool found with _id {tool_id!r}.")

    wa_config = wa_config or WebAvailabilityConfig()

    # 1) FAIR scores. score_one_tool already swallows a scoring failure and returns
    # "failed"; the guard here is only for the unexpected (a DB read raising).
    try:
        fair = {"status": score_one_tool(repos, tool, force=force)}
    except Exception as exc:
        logger.exception("FAIR stage failed for %s", tool_id)
        fair = {"status": "error", "error": _describe(exc)}

    # 2) Web availability -- runs regardless of what similarity will do.
    try:
        web = probe_tool_urls(tool, repos, url_checker, wa_config)
    except Exception as exc:
        logger.exception("web-availability stage failed for %s", tool_id)
        web = {"error": _describe(exc)}

    # 3) Similarity. An empty embedding cache (RuntimeError) or a model mismatch
    # (ValueError) is reported, not raised: FAIR and web above have already run.
    try:
        embed_fn = make_embedder()
        similarity = compute_record_similarity(
            repos,
            tool,
            embed_fn=embed_fn,
            model_name=model_name,
            k=k,
            reverse_update=reverse_update,
            reverse_candidates=reverse_candidates,
        )
    except Exception as exc:
        logger.warning("similarity stage skipped for %s: %s", tool_id, exc)
        similarity = {"error": _describe(exc)}

    failed_stages = [
        name
        for name, stage in (
            ("fair", fair),
            ("web_availability", web),
            ("similarity", similarity),
        )
        if stage.get("error") or stage.get("status") in ("error", "failed")
    ]

    result = {
        "tool_id": str(tool["_id"]),
        "tool_name": tool.get("data", {}).get("name", ""),
        "ok": not failed_stages,
        "failed_stages": failed_stages,
        "fair": fair,
        "web_availability": web,
        "similarity": similarity,
    }
    logger.info("enrich-tool complete for %s: %s", tool_id, result)
    return result


def _describe(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"
