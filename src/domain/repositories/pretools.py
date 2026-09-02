from typing import List, Optional, Protocol


class PretoolsRepository(Protocol):
    """The ``pretools`` collection of standardized software entries."""

    def get_all(self) -> List[dict]:
        """Every standardized software entry."""
        ...

    def get_by_id(self, entry_id: str) -> Optional[dict]:
        """The full pretools entry with this id, or None."""
        ...

    def get_by_ids(self, entry_ids) -> dict:
        """Fetch many entries at once in one ``$in`` query, keyed by ``_id``."""
        ...

    def exists(self, identifier: str) -> bool:
        """Whether an entry with this identifier exists."""
        ...

    def get_metadata(self, identifier: str) -> Optional[dict]:
        """The entry with this identifier, without its ``data`` field."""
        ...

    def upsert(self, identifier: str, document: dict) -> object:
        """Update the entry if it is already there, insert it otherwise."""
        ...

    def bulk_upsert(self, docs_by_id: dict) -> None:
        """Upsert many entries keyed by ``_id`` in a single round-trip."""
        ...
