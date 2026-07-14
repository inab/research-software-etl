"""
DatabaseAdapter defines the contract a concrete database driver must satisfy.

Only the repositories in ``infrastructure/db/`` talk to an adapter; application
code goes through those repositories and never sees a collection name or a
database verb. Implement this protocol to swap MongoDB for another store.

The protocol is *structural*: concrete adapters must not inherit from it. An
adapter that inherits and forgets a method would pick up the empty body defined
here and silently return ``None``; by staying structural, the same gap raises
``AttributeError`` at the call site.
"""

from typing import Any, Dict, Iterator, List, Optional, Protocol


class DatabaseAdapter(Protocol):
    def fetch_entry(self, collection_name: str, query: Dict[str, Any]) -> Optional[dict]:
        """Return the single document matching ``query``, or None."""
        ...

    def fetch_entries(self, collection_name: str, query: Dict[str, Any]) -> List[dict]:
        """Return every document matching ``query``, as a list."""
        ...

    def fetch_paginated_entries(
        self, collection_name: str, query: Dict[str, Any], page_size: int = 100
    ) -> Iterator[List[dict]]:
        """Yield documents matching ``query`` one page at a time."""
        ...

    def insert_one(self, collection_name: str, document: Dict[str, Any]) -> Any:
        """Insert ``document`` and return its identifier."""
        ...

    def update_entry(
        self, collection_name: str, identifier: str, data: Dict[str, Any]
    ) -> Any:
        """Set the fields of ``data`` on the entry with this identifier."""
        ...

    def entry_exists(self, collection_name: str, identifier: str) -> bool:
        """Whether an entry with this identifier exists."""
        ...

    def get_entry_metadata(
        self, collection_name: str, identifier: str
    ) -> Optional[dict]:
        """Return the entry with this identifier, without its ``data`` field."""
        ...

    def find(
        self,
        collection_name: str,
        query: Dict[str, Any],
        projection: Optional[Dict[str, Any]] = None,
        limit: int = 0,
        batch_size: int = 100,
        no_cursor_timeout: bool = True,
    ) -> Iterator[dict]:
        """Stream documents matching ``query``, reading only ``projection``."""
        ...

    def update_custom_upsert(
        self, collection_name: str, criteria: Dict[str, Any], data: Dict[str, Any]
    ) -> None:
        """Update the document matching ``criteria``, inserting it if there is none."""
        ...

    def bulk_write(
        self, collection_name: str, operations: List[Any], ordered: bool = False
    ) -> Any:
        """Apply a batch of write operations."""
        ...

    def distinct(
        self, collection_name: str, key: str, query: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        ...

    def create_index(self, collection_name: str, key: str, unique: bool = False) -> Any:
        ...

    def collection_exists(self, collection_name: str) -> bool:
        ...

    def drop_collection(self, collection_name: str) -> None:
        ...

    def rename_collection(
        self, collection_name: str, new_name: str, drop_target: bool = False
    ) -> None:
        """Rename a collection. Must be atomic: the run's final swap relies on it."""
        ...
