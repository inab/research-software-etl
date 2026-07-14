"""
The web-availability collection, keyed by URL rather than by tool id.

This repository exists mainly to keep ``pymongo.UpdateOne`` out of the
application layer. The use cases used to build driver objects themselves and hand
them to ``bulk_write``; they pass plain data now, and the batching writes below
are the only place that knows what a bulk operation looks like.
"""

import logging
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from pymongo import UpdateOne

from infrastructure.db.database_adapter import DatabaseAdapter

logger = logging.getLogger("rs-etl-pipeline")

RELEVANCE_TAG_FIELD = "relevance.is_relevant"


class WebAvailabilityRepository:
    def __init__(
        self, db_adapter: DatabaseAdapter, collection_name: str = "webAvailabilityDev"
    ):
        self.db_adapter = db_adapter
        self.collection_name = collection_name

    def relevant_urls(self, limit: int = 0, batch_size: int = 200) -> List[str]:
        """
        Every URL flagged relevant.

        Read fully into memory on purpose: the caller then makes a slow network
        check per URL, and holding a cursor open across thousands of them let the
        session idle past MongoDB's 30-minute timeout and die with CursorNotFound.
        The projection is just `_id`, so the whole set fits comfortably.
        """
        cursor = self.db_adapter.find(
            self.collection_name,
            query={RELEVANCE_TAG_FIELD: True},
            projection={"_id": 1},
            limit=limit if limit and limit > 0 else 0,
            batch_size=batch_size,
            no_cursor_timeout=True,
        )
        try:
            return [document.get("_id") for document in cursor]
        finally:
            close = getattr(cursor, "close", None)
            if close is not None:
                try:
                    close()
                except Exception:
                    pass

    def existing_urls(self, urls: Sequence[str]) -> Set[str]:
        return set(
            self.db_adapter.distinct(
                self.collection_name, "_id", {"_id": {"$in": list(urls)}}
            )
        )

    def append_availability(
        self,
        records: Iterable[Tuple[str, Dict[str, Any]]],
        keep_days: int,
        updated_at: str,
        updated_by: str,
    ) -> None:
        """
        Append one availability reading per URL, keeping only the last ``keep_days``.

        Never creates a document: a URL nobody flagged relevant is not monitored.
        """
        operations = [
            UpdateOne(
                {"_id": url},
                {
                    "$push": {
                        "data.availability": {"$each": [entry], "$slice": -keep_days}
                    },
                    "$set": {
                        "last_updated_at": updated_at,
                        "updated_by": updated_by,
                        "updated_logs": "daily-update",
                        "url": url,
                        "data.url": url,
                    },
                },
                upsert=False,
            )
            for url, entry in records
        ]
        self._bulk_write(operations)

    def tag_relevant(
        self,
        urls: Iterable[str],
        source: str,
        tagged_at: str,
        created_by: str,
        updated_by: str,
        log_label: str = "ensure-relevant-url",
    ) -> None:
        """
        Flag these URLs relevant, creating any that do not exist yet.

        Upserts over *every* relevant URL rather than only the missing ones, so a
        document created by some earlier process gets tagged too and starts being
        monitored.
        """
        operations = [
            UpdateOne(
                {"_id": url},
                {
                    "$set": {
                        RELEVANCE_TAG_FIELD: True,
                        "relevance.source": source,
                        "relevance.tagged_at": tagged_at,
                        "last_updated_at": tagged_at,
                        "updated_by": updated_by,
                        "updated_logs": log_label,
                        "url": url,
                    },
                    "$setOnInsert": {
                        "created_at": tagged_at,
                        "created_by": created_by,
                        "created_logs": log_label,
                        "data.url": url,
                        "data.availability": [],
                    },
                },
                upsert=True,
            )
            for url in urls
        ]
        self._bulk_write(operations)

    def _bulk_write(self, operations: List[UpdateOne]) -> Optional[Any]:
        if not operations:
            return None
        return self.db_adapter.bulk_write(
            self.collection_name, operations, ordered=False
        )
