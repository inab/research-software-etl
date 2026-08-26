"""
Application use case: update URL availability and maintain the relevant URL set.

This use case performs the web availability update by checking already tracked
relevant URLs and ensuring that newly discovered relevant tool URLs are added to the
tracking collection.

When to run:
- Periodically
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from domain.repositories import Repositories


DEFAULT_TIMEOUT = 15

RELEVANT_TYPES = {"rest", "web", "app", "suite", "workbench", "db", "soap", "sparql"}


def now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_availability_entry(
    code: Optional[int], access_time: Optional[float]
) -> Dict[str, Any]:
    return {"date": now_iso_z(), "code": code, "access_time": access_time}


@dataclass(frozen=True)
class WebAvailabilityConfig:
    """
    The knobs for one run of the stage.

    Collection names are not among them: they live in `PipelineConfig`, and the
    repositories this use case is handed already point at the right ones.
    """

    timeout: int = DEFAULT_TIMEOUT
    keep_days: int = 365
    created_by: str = "oeb-ingest"
    updated_by: str = "oeb-ingest"
    limit_web: int = 0
    limit_tools: int = 0
    batch_size: int = 200
    bulk_chunk: int = 500
    max_workers: int = 32
    dry_run: bool = False


@dataclass(frozen=True)
class WebAvailabilityResult:
    processed_existing_urls: int
    step1_errors: int
    tools_unique_urls: int
    tools_urls_already_present: int
    tools_urls_missing: int
    inserted_missing_urls: int
    retagged_existing_urls: int
    insert_errors: int


def _is_http_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _tool_is_relevant(types_value: Any) -> bool:
    if not isinstance(types_value, list):
        return False
    return any(isinstance(t, str) and t in RELEVANT_TYPES for t in types_value)


def _relevant_tool_urls(repos: Repositories, cfg: WebAvailabilityConfig) -> Set[str]:
    """Every webpage of every tool whose type makes it worth monitoring."""
    urls: Set[str] = set()
    for tool in repos.tools.iter_projected(
        query={},
        projection={"data.type": 1, "data.webpage": 1},
        limit=cfg.limit_tools,
        batch_size=cfg.batch_size,
    ):
        data = tool.get("data") or {}
        if not _tool_is_relevant(data.get("type")):
            continue

        webpages = data.get("webpage")
        if isinstance(webpages, list):
            urls.update(u.strip() for u in webpages if _is_http_url(u))

    return urls


def probe_tool_urls(
    tool: Dict[str, Any],
    repos: Repositories,
    url_checker,
    cfg: WebAvailabilityConfig,
) -> Dict[str, Any]:
    """
    Probe one tool's webpage URLs and record their availability.

    The per-record counterpart of :func:`run_update_web_availability`: instead of
    scanning the whole tools collection it takes a single tool document. Only
    tools whose type is worth monitoring contribute URLs, mirroring
    ``_relevant_tool_urls``.

    A URL new to the collection has no document yet, and ``append_availability``
    never creates one, so this tags first (which upserts the document) and then
    appends the reading -- the reverse of the batch order, which can rely on the
    daily pass to create documents later.
    """
    data = tool.get("data") or {}
    if not _tool_is_relevant(data.get("type")):
        return {"relevant": False, "probed": 0, "urls": []}

    webpages = data.get("webpage")
    urls = (
        sorted({u.strip() for u in webpages if _is_http_url(u)})
        if isinstance(webpages, list)
        else []
    )
    if not urls:
        return {"relevant": True, "probed": 0, "urls": []}

    if not cfg.dry_run:
        # Tag first so a brand-new URL's document exists before the reading lands.
        repos.web_availability.tag_relevant(
            urls=urls,
            source=repos.tools.collection_name,
            tagged_at=now_iso_z(),
            created_by=cfg.created_by,
            updated_by=cfg.updated_by,
            chunk_size=cfg.bulk_chunk,
        )

    readings: List[Tuple[str, Dict[str, Any]]] = []
    for url in urls:
        probe = url_checker.probe(url, timeout=cfg.timeout)
        readings.append(
            (url, build_availability_entry(probe.status, probe.access_time))
        )

    if not cfg.dry_run:
        repos.web_availability.append_availability(
            readings, cfg.keep_days, cfg.updated_by
        )

    return {"relevant": True, "probed": len(urls), "urls": urls}


def run_update_web_availability(
    cfg: WebAvailabilityConfig, repos: Repositories, url_checker
) -> WebAvailabilityResult:
    """
    Probing arbitrary tool URLs *is* this stage's job, so the checker that does it
    is injected rather than built here: that is the whole difference between a
    stage that can be tested offline and one that cannot.
    """
    if cfg.keep_days <= 0:
        raise ValueError("keep_days must be > 0")

    web = repos.web_availability

    # -----------------------------
    # Step 1: check ONLY the URLs already flagged relevant
    # -----------------------------
    readings: List[Tuple[str, Dict[str, Any]]] = []
    processed = 0
    errors = 0

    urls = [
        url
        for url in web.relevant_urls(limit=cfg.limit_web, batch_size=cfg.batch_size)
        if _is_http_url(url)
    ]

    try:
        # Probes are almost pure network wait, so they run concurrently; readings come
        # back in completion order and are flushed in the same bulk chunks as before.
        for url, probe in url_checker.probe_many(
            urls, timeout=cfg.timeout, max_workers=cfg.max_workers
        ):
            readings.append(
                (url, build_availability_entry(probe.status, probe.access_time))
            )
            processed += 1

            if len(readings) >= cfg.bulk_chunk:
                if not cfg.dry_run:
                    web.append_availability(readings, cfg.keep_days, cfg.updated_by)
                readings.clear()

    except Exception:
        errors += 1
        raise

    if readings and not cfg.dry_run:
        web.append_availability(readings, cfg.keep_days, cfg.updated_by)

    # -----------------------------
    # Step 2: ensure ONLY relevant tools' URLs exist + are tagged relevant
    # -----------------------------
    relevant_tool_urls = _relevant_tool_urls(repos, cfg)

    if not relevant_tool_urls:
        return WebAvailabilityResult(
            processed_existing_urls=processed,
            step1_errors=errors,
            tools_unique_urls=0,
            tools_urls_already_present=0,
            tools_urls_missing=0,
            inserted_missing_urls=0,
            retagged_existing_urls=0,
            insert_errors=0,
        )

    existing = web.existing_urls(relevant_tool_urls)
    missing = relevant_tool_urls - existing

    if not cfg.dry_run:
        # Tags *every* relevant URL, not just the missing ones: a document some
        # earlier process created gets flagged too, so Step 1 starts monitoring it.
        web.tag_relevant(
            urls=sorted(relevant_tool_urls),
            source=repos.tools.collection_name,
            tagged_at=now_iso_z(),
            created_by=cfg.created_by,
            updated_by=cfg.updated_by,
            chunk_size=cfg.bulk_chunk,
        )

    return WebAvailabilityResult(
        processed_existing_urls=processed,
        step1_errors=errors,
        tools_unique_urls=len(relevant_tool_urls),
        tools_urls_already_present=len(existing),
        tools_urls_missing=len(missing),
        inserted_missing_urls=len(missing),
        retagged_existing_urls=len(existing),
        insert_errors=0,
    )
