from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple, Protocol


class WebAvailabilityRepository(Protocol):
    """The web-availability collection, keyed by URL rather than by tool id."""

    def relevant_urls(self, limit: int = 0, batch_size: int = 200) -> List[str]:
        """Every URL flagged relevant."""
        ...

    def existing_urls(self, urls: Sequence[str]) -> Set[str]:
        """Which of ``urls`` already have a document."""
        ...

    def append_availability(
        self,
        records: Iterable[Tuple[str, Dict[str, Any]]],
        keep_days: int,
        updated_by: str,
    ) -> None:
        """Append one availability reading per URL, keeping the last ``keep_days``."""
        ...

    def tag_relevant(
        self,
        urls: Iterable[str],
        source: str,
        tagged_at: str,
        created_by: str,
        updated_by: str,
        log_label: str = "ensure-relevant-url",
        chunk_size: int = 500,
    ) -> int:
        """Flag these URLs relevant, creating any that do not exist yet."""
        ...
