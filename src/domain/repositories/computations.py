from typing import Any, Dict, List, Optional, Protocol


class ComputationsRepository(Protocol):
    """The ``computations`` collection every statistic lands in."""

    def save(self, document: Dict[str, Any]) -> Any:
        """Append a computed statistic."""
        ...

    def find_one(self, query: Dict[str, Any]) -> Optional[dict]:
        """The first computation matching a query, or None."""
        ...

    def upsert(self, match: Dict[str, Any], document: Dict[str, Any]) -> None:
        """Update the document matching ``match``, or insert it if there is none."""
        ...

    def find_by_variable(self, variable: str, tag: Optional[str] = None) -> List[dict]:
        """Every computation of one kind, optionally for one tag-scoped subset."""
        ...
