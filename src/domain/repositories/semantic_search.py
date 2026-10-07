from typing import Any, Dict, Iterable, Optional, Protocol


class SemanticSearchRepository(Protocol):
    """
    The ``semantic_search`` collection: synthetic search queries, one document per
    tool, keyed by ``tool_id``.
    """

    def upsert_by_tool_id(self, document: Dict[str, Any]) -> None:
        """Upsert one tool's query document, matched on its ``tool_id``."""
        ...

    def find_by_tool_id(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """One tool's query document, or ``None``."""
        ...

    def fingerprints(self) -> Dict[str, Dict[str, Any]]:
        """``{tool_id: {input_hash, prompt_version}}`` for every stored document."""
        ...

    def delete_except(self, tool_ids: Iterable[str]) -> int:
        """Delete the documents of every tool not in ``tool_ids``; return the count."""
        ...

    def ensure_tool_id_index(self) -> None:
        """Create the unique index on ``tool_id`` (warns rather than raises)."""
        ...
