from typing import Any, Dict, List, Optional, Protocol, Sequence, Tuple


class EmbeddingsRepository(Protocol):
    """
    The per-tool embedding cache, keyed by ``tool_id``.

    Holds one dense vector per tool so the incremental (``enrich-tool``) path can
    embed a single record and compare it against every other tool without
    re-embedding the whole corpus. Vectors are only comparable when produced by
    the same model, so each document records the ``model`` that made it.
    """

    def is_empty(self) -> bool:
        """Whether the cache has no documents."""
        ...

    def upsert_by_tool_id(
        self,
        tool_id: str,
        tool_name: str,
        text: str,
        vector: Sequence[float],
        model: str,
        version: Optional[str],
    ) -> None:
        """Upsert one tool's embedding, matched on ``tool_id``."""
        ...

    def get(self, tool_id: str) -> Optional[Dict[str, Any]]:
        """One tool's embedding document, or ``None``."""
        ...

    def load_all(self) -> Tuple[List[str], List[str], Any, Optional[str]]:
        """
        Every cached embedding as ``(ids, names, matrix, model)``.

        ``matrix`` is a float32 array of shape ``(N, dim)`` (returned as ``Any`` so
        the domain protocol stays free of a numpy import). ``model`` is the single
        model the cache was built with (``None`` when the cache is empty); callers
        use it to refuse mixing incompatible vectors.
        """
        ...

    def ensure_tool_id_index(self) -> None:
        """Create the unique index on ``tool_id`` (warns rather than raises)."""
        ...
