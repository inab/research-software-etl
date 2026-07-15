from __future__ import annotations

from typing import Any, Iterator, List, Protocol


class ToolsRepository(Protocol):
    """
    The ``tools`` collection (the pipeline's final output) and its ``tools_staging``
    twin. Both slots are the same shape, pointed at different collection names.
    """

    collection_name: str

    def insert(self, document: dict) -> Any:
        """Insert a merged tool entry and return its id."""
        ...

    def get_all(self) -> List[dict]:
        """Every tool document."""
        ...

    def find(self, query: dict) -> List[dict]:
        """Tools matching a query."""
        ...

    def iter_projected(
        self, query: dict, projection: dict, limit: int = 0, batch_size: int = 100
    ) -> Iterator[dict]:
        """Stream tools reading only the fields asked for."""
        ...

    def iter_lineage(self) -> Iterator[dict]:
        """Stream each tool's id, source lineage and first-seen timestamp."""
        ...

    def for_collection(self, collection_name: str) -> ToolsRepository:
        """The same collection shape, pointed at a different name."""
        ...

    def exists(self) -> bool:
        """Whether the collection exists."""
        ...

    def drop(self) -> None:
        """Drop the collection."""
        ...

    def rename_to(self, new_name: str, drop_target: bool = False) -> None:
        """Rename the collection (atomically)."""
        ...
