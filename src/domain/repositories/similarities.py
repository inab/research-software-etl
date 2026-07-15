from typing import Any, Dict, Protocol


class SimilaritiesRepository(Protocol):
    """The ``similarities`` collection, keyed by ``tool_id``."""

    def is_empty(self) -> bool:
        """Whether the collection has no documents."""
        ...

    def upsert_by_tool_id(self, document: Dict[str, Any]) -> None:
        """Upsert one similarity document, matched on its ``tool_id``."""
        ...

    def ensure_tool_id_index(self) -> None:
        """Create the unique index on ``tool_id`` (warns rather than raises)."""
        ...
