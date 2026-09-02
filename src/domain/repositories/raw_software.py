from datetime import datetime
from typing import Iterator, List, Optional, Protocol


class RawSoftwareRepository(Protocol):
    """The raw source collection (``alambique``), read during transformation."""

    def get_raw_documents_from_source(
        self, source: str, updated_since: Optional[datetime] = None
    ) -> Iterator[List[dict]]:
        """Yield raw documents for one source, one page at a time.

        When ``updated_since`` is given, only documents whose ``@last_updated_at``
        is on or after that datetime are yielded; ``None`` yields all entries.
        """
        ...
