# The similarities collection: the front-end fetches a tool's neighbours by tool_id.

import logging
from typing import Any, Dict, Optional

from infrastructure.db.database_adapter import DatabaseAdapter

logger = logging.getLogger("rs-etl-pipeline")


class SimilaritiesRepository:
    def __init__(
        self, db_adapter: DatabaseAdapter, collection_name: str = "similaritiesDev"
    ):
        self.db_adapter = db_adapter
        self.collection_name = collection_name

    def is_empty(self) -> bool:
        return self.db_adapter.fetch_entry(self.collection_name, {}) is None

    def upsert_by_tool_id(self, document: Dict[str, Any]) -> None:
        self.db_adapter.update_custom_upsert(
            self.collection_name, {"tool_id": document["tool_id"]}, document
        )

    def find_by_tool_id(self, tool_id: str) -> Optional[Dict[str, Any]]:
        return self.db_adapter.fetch_entry(self.collection_name, {"tool_id": tool_id})

    def ensure_tool_id_index(self) -> None:
        """
        The front-end looks tools up by ``tool_id``, and one document per tool is the
        invariant the upsert above relies on. Failing to create it is not fatal --
        the stage still writes correct data -- so this warns rather than raises,
        as the code it replaces did.
        """
        try:
            self.db_adapter.create_index(self.collection_name, "tool_id", unique=True)
        except Exception as exc:
            logger.warning("Could not create index on tool_id: %s", exc)
