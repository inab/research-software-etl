# The computations collection: everything the stats stages derive from the tools.

import logging
from typing import Any, Dict, List, Optional

from infrastructure.db.database_adapter import DatabaseAdapter

logger = logging.getLogger("rs-etl-pipeline")


class ComputationsRepository:
    """
    Where every statistic lands.

    Nearly the whole stats layer is one operation -- append a computed document --
    which is why sixteen services need nothing from this beyond `save`.
    """

    def __init__(
        self, db_adapter: DatabaseAdapter, collection_name: str = "computationsDev"
    ):
        self.db_adapter = db_adapter
        self.collection_name = collection_name

    def save(self, document: Dict[str, Any]) -> Any:
        """Append a computed statistic."""
        return self.db_adapter.insert_one(self.collection_name, document)

    def find(self, query: Dict[str, Any]) -> List[dict]:
        return self.db_adapter.fetch_entries(self.collection_name, query)

    def find_one(self, query: Dict[str, Any]) -> Optional[dict]:
        return self.db_adapter.fetch_entry(self.collection_name, query)

    def upsert(self, match: Dict[str, Any], document: Dict[str, Any]) -> None:
        """Update the document matching ``match``, or insert it if there is none."""
        self.db_adapter.update_custom_upsert(self.collection_name, match, document)

    def find_by_variable(self, variable: str, tag: Optional[str] = None) -> List[dict]:
        """
        Every computation of one kind ("FAIR_scores", "types_count", ...), optionally
        for one tag-scoped subset of the tools.
        """
        query: Dict[str, Any] = {"variable": variable}
        if tag is not None:
            query["tags"] = tag
        return self.find(query)
