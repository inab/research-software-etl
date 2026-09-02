from typing import Any, List, Optional, Protocol


class PublicationRepository(Protocol):
    """The ``publications`` metadata collection."""

    def get_by_id(self, identifier: Any) -> Optional[dict]:
        """A publication metadata entry by its identifier."""
        ...

    def get_all(self) -> List[dict]:
        """Every publication metadata entry."""
        ...

    def find_by_doi(self, doi: str) -> Optional[dict]:
        """A publication metadata entry by DOI."""
        ...

    def find_by_title(self, title: str) -> Optional[dict]:
        """A publication metadata entry by title."""
        ...

    def find_by_url(self, url: str) -> Optional[dict]:
        """A publication metadata entry by URL."""
        ...

    def find_by_pmid(self, pmid: str) -> Optional[dict]:
        """A publication metadata entry by PMID."""
        ...

    def find_by_pmcid(self, pmcid: str) -> Optional[dict]:
        """A publication metadata entry by PMCID."""
        ...

    def find_existing_by_field(self, field: str, values: list) -> List[dict]:
        """Publication entries whose ``data.<field>`` is in ``values`` (one ``$in`` query)."""
        ...

    def save_entry(self, document: dict) -> Any:
        """Insert a publication metadata entry and return its id."""
        ...

    def save_many(self, documents: List[dict]) -> List[Any]:
        """Insert many publication metadata entries in one round-trip; return their ids."""
        ...
