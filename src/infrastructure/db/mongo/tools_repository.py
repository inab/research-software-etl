# This repository connects to the tools collection: the pipeline's final output.

import logging
from typing import Any, Iterator

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

    def iter_lineage(self) -> Iterator[dict]:
        """
        Stream just enough of each tool to work out what it is: its id, the pretools
        entries it came from, and when it first appeared.

        Deliberately projected. The merge stage only needs lineage to carry ids
        forward, and pulling ~50k full tool documents to read three fields would
        cost far more memory than the job needs.
        """
        return self.db_adapter.find(
            self.collection_name,
            {},
            projection={"_id": 1, "source": 1, "first_seen": 1, "timestamp": 1},
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
