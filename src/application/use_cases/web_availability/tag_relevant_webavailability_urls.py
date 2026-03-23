# NOTE:
# The webAvailability collection was initially populated from a broader dataset
# that included both relevant (web-based/deployable) and non-relevant (cmd, etc) 
# URL records (from OEB tools monitoring). Because some of the non-relevant 
# records could still have future value, they were not removed.
#
# Instead, relevance is modeled explicitly through the `is_relevant` flag. This
# makes it possible to preserve the full imported dataset while restricting the
# daily monitoring workflow to the subset of URLs that correspond to relevant
# tool webpages.
# 
# ---> This use case was used once and is not meant to be executed periodically

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from pymongo import UpdateOne

from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


RELEVANT_TYPES = {"rest", "web", "app", "suite", "workbench", "db", "soap", "sparql"}


def now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_http_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


@dataclass(frozen=True)
class TagRelevantWebAvailabilityConfig:
    tools_collection: str = "toolsDev"
    web_collection: str = "webAvailabilityDev"
    created_by: str = "oeb-ingest"
    updated_by: str = "oeb-ingest"
    tag_field: str = "is_relevant"   # top-level field
    tag_source: str = "toolsDev"
    bulk_chunk: int = 500
    batch_size: int = 200
    limit_tools: int = 0  # 0 = all
    dry_run: bool = False


@dataclass(frozen=True)
class TagRelevantWebAvailabilityResult:
    tools_scanned: int
    tools_matched: int
    relevant_urls_found: int
    upserts_sent: int


def run_tag_relevant_webavailability_urls(
    cfg: TagRelevantWebAvailabilityConfig,
) -> TagRelevantWebAvailabilityResult:
    """
    Tag (and upsert) webAvailabilityDev docs based on toolsDev:
    - If tool.data.type intersects RELEVANT_TYPES, then every URL in tool.data.webpage is relevant.
    - For each relevant URL, upsert into webAvailabilityDev with empty availability on insert.
    - Tag field (default: is_relevant) is set to True (top-level).
    """

    # 1) Collect relevant URLs from toolsDev
    cursor = mongo_adapter.find(
        cfg.tools_collection,
        query={},
        projection={"data.type": 1, "data.webpage": 1},
        limit=cfg.limit_tools if cfg.limit_tools and cfg.limit_tools > 0 else 0,
        batch_size=cfg.batch_size,
        no_cursor_timeout=True,
    )

    relevant_urls: Set[str] = set()
    tools_scanned = 0
    tools_matched = 0

    try:
        for doc in cursor:
            tools_scanned += 1
            data = doc.get("data") or {}
            types = data.get("type")

            if not isinstance(types, list):
                continue

            if not any(isinstance(t, str) and t in RELEVANT_TYPES for t in types):
                continue

            tools_matched += 1
            webpages = data.get("webpage")

            if isinstance(webpages, list):
                for u in webpages:
                    if _is_http_url(u):
                        relevant_urls.add(u.strip())
    finally:
        try:
            cursor.close()
        except Exception:
            pass

    if not relevant_urls:
        return TagRelevantWebAvailabilityResult(
            tools_scanned=tools_scanned,
            tools_matched=tools_matched,
            relevant_urls_found=0,
            upserts_sent=0,
        )

    # 2) Upsert + tag into webAvailabilityDev
    ops: List[UpdateOne] = []
    upserts_sent = 0
    now = now_iso_z()

    for url in relevant_urls:
        ops.append(
            UpdateOne(
                {"_id": url},
                {
                    # Always set tag + update metadata
                    "$set": {
                        cfg.tag_field: True,  # top-level
                        "relevance.source": cfg.tag_source,
                        "relevance.tagged_at": now,

                        "last_updated_at": now,
                        "updated_by": cfg.updated_by,
                        "updated_logs": "tag-relevant-urls",
                    },
                    # Only on insert create missing fields using dotted keys (NO "data": {...})
                    "$setOnInsert": {
                        "created_at": now,
                        "created_by": cfg.created_by,
                        "created_logs": "tag-relevant-urls",
                        "url": url,
                        "data.url": url,
                        "data.availability": [],
                    },
                },
                upsert=True,
            )
        )

        if len(ops) >= cfg.bulk_chunk:
            upserts_sent += len(ops)
            if not cfg.dry_run:
                mongo_adapter.bulk_write(cfg.web_collection, ops, ordered=False)
            ops.clear()

    if ops:
        upserts_sent += len(ops)
        if not cfg.dry_run:
            mongo_adapter.bulk_write(cfg.web_collection, ops, ordered=False)
        ops.clear()

    return TagRelevantWebAvailabilityResult(
        tools_scanned=tools_scanned,
        tools_matched=tools_matched,
        relevant_urls_found=len(relevant_urls),
        upserts_sent=upserts_sent,
    )