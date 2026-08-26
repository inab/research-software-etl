# The per-tool embedding cache: the `enrich-tool` path reads it so a single tool
# embeds only itself instead of re-embedding the whole corpus.

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from bson import Binary

from infrastructure.db.database_adapter import DatabaseAdapter

logger = logging.getLogger("rs-etl-pipeline")


def _pack(vector: Sequence[float]) -> Binary:
    """Pack a vector as raw little-endian float32 bytes (BSON Binary).

    Storing packed bytes instead of a BSON array of doubles roughly halves the
    on-disk size and skips per-element BSON decoding on read.
    """
    return Binary(np.asarray(vector, dtype="<f4").tobytes())


def _unpack(value: Any) -> np.ndarray:
    return np.frombuffer(bytes(value), dtype="<f4")


class EmbeddingsRepository:
    def __init__(
        self, db_adapter: DatabaseAdapter, collection_name: str = "toolEmbeddingsDev"
    ):
        self.db_adapter = db_adapter
        self.collection_name = collection_name

    def is_empty(self) -> bool:
        return self.db_adapter.fetch_entry(self.collection_name, {}) is None

    def upsert_by_tool_id(
        self,
        tool_id: str,
        tool_name: str,
        text: str,
        vector: Sequence[float],
        model: str,
        version: Optional[str],
    ) -> None:
        packed = _pack(vector)
        document = {
            "tool_id": tool_id,
            "tool_name": tool_name,
            "text": text,
            "embedding": packed,
            "dim": len(packed) // 4,
            "model": model,
            "version": version,
            "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self.db_adapter.update_custom_upsert(
            self.collection_name, {"tool_id": tool_id}, document
        )

    def get(self, tool_id: str) -> Optional[Dict[str, Any]]:
        return self.db_adapter.fetch_entry(self.collection_name, {"tool_id": tool_id})

    def load_all(self) -> Tuple[List[str], List[str], np.ndarray, Optional[str]]:
        docs = self.db_adapter.fetch_entries(self.collection_name, {})
        if not docs:
            return [], [], np.empty((0, 0), dtype=np.float32), None

        ids: List[str] = []
        names: List[str] = []
        rows: List[np.ndarray] = []
        for doc in docs:
            ids.append(doc["tool_id"])
            names.append(doc.get("tool_name", ""))
            rows.append(_unpack(doc["embedding"]))

        matrix = np.vstack(rows).astype(np.float32)
        model = docs[0].get("model")
        return ids, names, matrix, model

    def ensure_tool_id_index(self) -> None:
        """
        One embedding per tool is the invariant the upsert relies on. Failing to
        create the index is not fatal, so this warns rather than raises, mirroring
        the similarities repository.
        """
        try:
            self.db_adapter.create_index(self.collection_name, "tool_id", unique=True)
        except Exception as exc:
            logger.warning("Could not create index on tool_id: %s", exc)
