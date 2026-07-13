# This repository connects to the tools collection: the pipeline's final output.

import logging
from typing import Any

from infrastructure.db.database_adapter import DatabaseAdapter

logger = logging.getLogger("rs-etl-pipeline")


class ToolsRepository:
    def __init__(self, db_adapter: DatabaseAdapter, collection_name: str = "toolsDev"):
        self.db_adapter = db_adapter
        self.collection_name = collection_name

    def insert(self, document: dict) -> Any:
        """Insert a merged tool entry and return its id."""
        return self.db_adapter.insert_one(self.collection_name, document)

    def get_all(self) -> list[dict]:
        return self.db_adapter.fetch_entries(self.collection_name, {})

    def set_license(self, tool_id: str, license_value: Any) -> None:
        self.db_adapter.update_entry(
            self.collection_name, tool_id, {"data.license": license_value}
        )
