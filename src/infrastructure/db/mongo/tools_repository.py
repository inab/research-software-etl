# This repository connects to the tools collection: the pipeline's final output.

import logging
from typing import Any, Iterator, Optional

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import UpdateOne

from infrastructure.db.database_adapter import DatabaseAdapter

logger = logging.getLogger("rs-etl-pipeline")


class ToolsRepository:
    def __init__(self, db_adapter: DatabaseAdapter, collection_name: str = "toolsDev"):
        self.db_adapter = db_adapter
        self.collection_name = collection_name

    def insert(self, document: dict) -> Any:
        """Insert a merged tool entry and return its id."""
        return self.db_adapter.insert_one(self.collection_name, document)

    def insert_many(self, documents: list[dict]) -> list[Any]:
        """Insert many merged tool entries in one round-trip; return their ids."""
        return self.db_adapter.insert_many(self.collection_name, documents)

    def get_all(self) -> list[dict]:
        return self.db_adapter.fetch_entries(self.collection_name, {})

    def find(self, query: dict) -> list[dict]:
        """Tools matching a query -- the stats stages scope by `{"data.tags": tag}`."""
        return self.db_adapter.fetch_entries(self.collection_name, query)

    def find_by_id(self, tool_id: str) -> Optional[dict]:
        """
        One tool by its ``_id``. Tool ids are ObjectIds, so a hex string is coerced
        to one; a non-hex id (should not happen for tools) falls back to matching
        the raw value.
        """
        try:
            query = {"_id": ObjectId(tool_id)}
        except (InvalidId, TypeError):
            query = {"_id": tool_id}
        return self.db_adapter.fetch_entry(self.collection_name, query)

    def iter_projected(
        self, query: dict, projection: dict, limit: int = 0, batch_size: int = 100
    ) -> Iterator[dict]:
        """Stream tools reading only the fields asked for."""
        return self.db_adapter.find(
            self.collection_name,
            query,
            projection=projection,
            limit=limit if limit and limit > 0 else 0,
            batch_size=batch_size,
            no_cursor_timeout=True,
        )

    def iter_lineage(self) -> Iterator[dict]:
        """
        Stream just enough of each tool to work out what it is: its id, the pretools
        entries it came from, when it first appeared (``created_at``), and its last
        update time (``last_updated_at``) and content fingerprint (so merge can tell
        whether the tool actually changed).

        The old field names (``first_seen`` / ``timestamp``) are projected too, so a
        collection written before the rename still hands its dates to
        ``previous_tool_from_document`` on the first post-rename run.

        Deliberately projected. The merge stage only needs lineage to carry ids
        forward, and pulling ~50k full tool documents to read a handful of fields
        would cost far more memory than the job needs.
        """
        return self.db_adapter.find(
            self.collection_name,
            {},
            projection={
                "_id": 1,
                "source": 1,
                "created_at": 1,
                "last_updated_at": 1,
                "first_seen": 1,
                "timestamp": 1,
                "content_hash": 1,
            },
        )

    def for_collection(self, collection_name: str) -> "ToolsRepository":
        """
        The same collection shape, pointed at a different name.

        Lets a use case talk about an archive ("toolsDev_archive_<run_id>") without
        reaching past the repository for a raw adapter.
        """
        return ToolsRepository(self.db_adapter, collection_name)

    def exists(self) -> bool:
        return self.db_adapter.collection_exists(self.collection_name)

    def list_by_prefix(self, prefix: str) -> list[str]:
        """
        Collection names starting with ``prefix`` -- how finalize_run finds the
        ``toolsDev_archive_*`` collections it prunes, without naming a collection
        in the application layer.
        """
        return [
            name
            for name in self.db_adapter.list_collection_names()
            if name.startswith(prefix)
        ]

    def drop(self) -> None:
        self.db_adapter.drop_collection(self.collection_name)

    def rename_to(self, new_name: str, drop_target: bool = False) -> None:
        self.db_adapter.rename_collection(
            self.collection_name, new_name, drop_target=drop_target
        )

    def set_license(self, tool_id: Any, license_value: Any) -> None:
        self.db_adapter.update_entry(
            self.collection_name, tool_id, {"data.license": license_value}
        )

    def bulk_set_licenses(self, licenses_by_id: dict) -> None:
        """
        Write many normalized license lists in one round-trip, keyed by ``_id``.

        Replaces a per-tool ``set_license`` loop (one latency-bound update each --
        ~18k of them on a full run) with a single ``bulk_write``. The driver
        ``UpdateOne`` stays here in the repository. Missing tools are not created
        (``upsert=False``): this only rewrites the license of tools that exist.
        """
        operations = [
            UpdateOne({"_id": tool_id}, {"$set": {"data.license": license_value}})
            for tool_id, license_value in licenses_by_id.items()
        ]
        if operations:
            self.db_adapter.bulk_write(self.collection_name, operations)
