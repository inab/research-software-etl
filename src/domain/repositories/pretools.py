from typing import List, Optional, Protocol


class PretoolsRepository(Protocol):
    """The ``pretools`` collection of standardized software entries."""

    def get_all(self) -> List[dict]:
        """Every standardized software entry."""
        ...

    def get_by_id(self, entry_id: str) -> Optional[dict]:
        """The full pretools entry with this id, or None."""
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
