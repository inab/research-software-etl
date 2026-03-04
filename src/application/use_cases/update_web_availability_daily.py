from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from pymongo import UpdateOne

from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


DEFAULT_TIMEOUT = 15
HEADERS = {
    "User-Agent": "oeb-web-availability-daily/1.0 (+monitor)",
    "Accept": "*/*",
}

RELEVANT_TYPES = {"rest", "web", "app", "suite", "workbench", "db", "soap", "sparql"}
RELEVANCE_TAG_FIELD = "is_relevant"  # top-level boolean


def now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def check_url(url: str, timeout: int = DEFAULT_TIMEOUT) -> Tuple[Optional[int], Optional[float]]:
    session = requests.Session()

    def _do(method: str) -> Tuple[Optional[int], Optional[float]]:
        start = time.perf_counter()
        try:
            resp = session.request(method, url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            elapsed = time.perf_counter() - start
            return resp.status_code, elapsed
        except Exception:
            return None, None

    code, t = _do("HEAD")
    if code is None or code in (405, 403, 400):
        return _do("GET")
    return code, t


def build_availability_entry(code: Optional[int], access_time: Optional[float]) -> Dict[str, Any]:
    return {"date": now_iso_z(), "code": code, "access_time": access_time}


@dataclass(frozen=True)
class WebAvailabilityDailyConfig:
    web_collection: str = "webAvailabilityDev"
    tools_collection: str = "ToolsDev"
    timeout: int = DEFAULT_TIMEOUT
    keep_days: int = 365
    created_by: str = "oeb-ingest"
    updated_by: str = "oeb-ingest"
    limit_web: int = 0
    limit_tools: int = 0
    batch_size: int = 200
    bulk_chunk: int = 500
    dry_run: bool = False


@dataclass(frozen=True)
class WebAvailabilityDailyResult:
    processed_existing_urls: int
    step1_errors: int
    tools_unique_urls: int
    tools_urls_already_present: int
    tools_urls_missing: int
    inserted_missing_urls: int
    insert_errors: int


def _is_http_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


def _tool_is_relevant(types_value: Any) -> bool:
    if not isinstance(types_value, list):
        return False
    return any(isinstance(t, str) and t in RELEVANT_TYPES for t in types_value)


def run_update_web_availability_daily(cfg: WebAvailabilityDailyConfig) -> WebAvailabilityDailyResult:
    if cfg.keep_days <= 0:
        raise ValueError("keep_days must be > 0")

    # -----------------------------
    # Step 1: update ONLY relevant URLs in webAvailabilityDev
    # -----------------------------
    cursor = mongo_adapter.find(
        cfg.web_collection,
        query={RELEVANCE_TAG_FIELD: True},  # <-- only relevant
        projection={"_id": 1},
        limit=cfg.limit_web if cfg.limit_web and cfg.limit_web > 0 else 0,
        batch_size=cfg.batch_size,
        no_cursor_timeout=True,
    )

    updates: List[UpdateOne] = []
    processed = 0
    errors = 0

    try:
        for doc in cursor:
            url = doc.get("_id")
            if not _is_http_url(url):
                continue

            code, access_time = check_url(url, timeout=cfg.timeout)
            entry = build_availability_entry(code, access_time)

            updates.append(
                UpdateOne(
                    {"_id": url},
                    {
                        "$push": {
                            "data.availability": {
                                "$each": [entry],
                                "$slice": -cfg.keep_days,
                            }
                        },
                        "$set": {
                            "last_updated_at": now_iso_z(),
                            "updated_by": cfg.updated_by,
                            "updated_logs": "daily-update",
                            "url": url,
                            "data.url": url,
                        },
                    },
                    upsert=False,
                )
            )
            processed += 1

            if len(updates) >= cfg.bulk_chunk:
                if not cfg.dry_run:
                    mongo_adapter.bulk_write(cfg.web_collection, updates, ordered=False)
                updates.clear()

    except Exception:
        errors += 1
        raise
    finally:
        try:
            cursor.close()
        except Exception:
            pass

    if updates:
        if not cfg.dry_run:
            mongo_adapter.bulk_write(cfg.web_collection, updates, ordered=False)
        updates.clear()

    # -----------------------------
    # Step 2: ensure ONLY relevant tools' URLs exist + are tagged relevant
    # -----------------------------
    tool_cursor = mongo_adapter.find(
        cfg.tools_collection,
        query={},  # could be optimized if you index data.type; see note below
        projection={"data.type": 1, "data.webpage": 1},
        limit=cfg.limit_tools if cfg.limit_tools and cfg.limit_tools > 0 else 0,
        batch_size=cfg.batch_size,
        no_cursor_timeout=True,
    )

    relevant_tool_urls: Set[str] = set()
    try:
        for tdoc in tool_cursor:
            data = tdoc.get("data") or {}
            if not _tool_is_relevant(data.get("type")):
                continue

            webpages = data.get("webpage")
            if isinstance(webpages, list):
                for u in webpages:
                    if _is_http_url(u):
                        relevant_tool_urls.add(u.strip())
    finally:
        try:
            tool_cursor.close()
        except Exception:
            pass

    if not relevant_tool_urls:
        return WebAvailabilityDailyResult(
            processed_existing_urls=processed,
            step1_errors=errors,
            tools_unique_urls=0,
            tools_urls_already_present=0,
            tools_urls_missing=0,
            inserted_missing_urls=0,
            insert_errors=0,
        )

    existing = set(
        mongo_adapter.distinct(cfg.web_collection, "_id", {"_id": {"$in": list(relevant_tool_urls)}})
    )
    missing = [u for u in relevant_tool_urls if u not in existing]

    # Instead of InsertOne docs, use UpdateOne(upsert=True) so:
    # - missing docs are created with empty availability
    # - existing docs get tagged as relevant (top-level)
    upserts: List[UpdateOne] = []
    inserted = 0
    insert_errors = 0
    now = now_iso_z()

    for url in missing:
        try:
            upserts.append(
                UpdateOne(
                    {"_id": url},
                    {
                        "$set": {
                            RELEVANCE_TAG_FIELD: True,           # <-- tag relevant
                            "relevance.source": "ToolsDev",
                            "relevance.tagged_at": now,
                            "last_updated_at": now,
                            "updated_by": cfg.updated_by,
                            "updated_logs": "ensure-relevant-url",
                            "url": url,
                        },
                        "$setOnInsert": {
                            "created_at": now,
                            "created_by": cfg.created_by,
                            "created_logs": "ensure-relevant-url",
                            "data.url": url,
                            "data.availability": [],            # <-- empty availability on insert
                        },
                    },
                    upsert=True,
                )
            )
            inserted += 1

            if len(upserts) >= cfg.bulk_chunk:
                if not cfg.dry_run:
                    mongo_adapter.bulk_write(cfg.web_collection, upserts, ordered=False)
                upserts.clear()

        except Exception:
            insert_errors += 1
            continue

    if upserts:
        if not cfg.dry_run:
            mongo_adapter.bulk_write(cfg.web_collection, upserts, ordered=False)
        upserts.clear()

    return WebAvailabilityDailyResult(
        processed_existing_urls=processed,
        step1_errors=errors,
        tools_unique_urls=len(relevant_tool_urls),
        tools_urls_already_present=len(existing),
        tools_urls_missing=len(missing),
        inserted_missing_urls=inserted,
        insert_errors=insert_errors,
    )