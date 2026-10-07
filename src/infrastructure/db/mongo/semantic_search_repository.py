# The semantic-search collection: synthetic search queries per tool, keyed by tool_id.

import logging
from typing import Any, Dict, Iterable

from infrastructure.db.database_adapter import DatabaseAdapter

logger = logging.getLogger("rs-etl-pipeline")


class SemanticSearchRepository:
    def __init__(
        self, db_adapter: DatabaseAdapter, collection_name: str = "semantic_search"
    ):
        self.db_adapter = db_adapter
        self.collection_name = collection_name

    def upsert_by_tool_id(self, document: Dict[str, Any]) -> None:
        self.db_adapter.update_custom_upsert(
            self.collection_name, {"tool_id": document["tool_id"]}, document
        )

    def find_by_tool_id(self, tool_id: str) -> Dict[str, Any] | None:
        return self.db_adapter.fetch_entry(self.collection_name, {"tool_id": tool_id})

    def fingerprints(self) -> Dict[str, Dict[str, Any]]:
        """
        What each stored document was generated from, keyed by ``tool_id``.

        Projected: the stage compares these against the live tools to decide what
        to (re)generate, and has no use for the queries themselves.
        """
        cursor = self.db_adapter.find(
            self.collection_name,
            {},
            projection={"_id": 0, "tool_id": 1, "input_hash": 1, "prompt_version": 1},
            batch_size=5000,
        )
        return {doc["tool_id"]: doc for doc in cursor if "tool_id" in doc}

    def delete_except(self, tool_ids: Iterable[str]) -> int:
        """Delete the documents of every tool not in ``tool_ids``; return the count."""
        return self.db_adapter.delete_many(
            self.collection_name, {"tool_id": {"$nin": list(tool_ids)}}
        )

    def ensure_tool_id_index(self) -> None:
        """
        One document per tool is the invariant the upsert above relies on. Failing to
        create the index is not fatal, so this warns rather than raises, mirroring
        the similarities repository.
        """
        try:
            self.db_adapter.create_index(self.collection_name, "tool_id", unique=True)
        except Exception as exc:
            logger.warning("Could not create index on tool_id: %s", exc)
