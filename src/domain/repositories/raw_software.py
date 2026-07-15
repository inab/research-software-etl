from typing import Iterator, List, Protocol


class RawSoftwareRepository(Protocol):
    """The raw source collection (``alambique``), read during transformation."""

    def get_raw_documents_from_source(self, source: str) -> Iterator[List[dict]]:
        """Yield raw documents for one source, one page at a time."""
        ...
