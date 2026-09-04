"""
Embed tool descriptions and compute pairwise cosine-similarity top-K neighbours.

The full N×N similarity matrix would exceed available RAM at ~50K tools, so
similarity is computed in chunks: each chunk produces a (chunk_size × N) slab,
from which only the top-K indices are retained before moving to the next chunk.
"""

import logging
from datetime import datetime, timezone

import numpy as np

logger = logging.getLogger(__name__)


def build_text(tool_data: dict) -> str:
    """Concatenate the longest description with topics and operations terms.

    Falls back to the 'help' documentation item when description is absent.
    """
    descriptions = [d for d in tool_data.get("description", []) if d and d.strip()]
    if descriptions:
        text = max(descriptions, key=len)
    else:
        help_item = next(
            (
                item for item in tool_data.get("documentation", [])
                if item.get("type") == "help" and item.get("content")
            ),
            None,
        )
        text = help_item["content"].strip() if help_item else ""

    topics = [t["term"] for t in tool_data.get("topics", []) if t.get("term")]
    operations = [o["term"] for o in tool_data.get("operations", []) if o.get("term")]

    if topics:
        text += " Topics: " + ", ".join(topics) + "."
    if operations:
        text += " Operations: " + ", ".join(operations) + "."

    return text.strip()


def _load_model(model_name: str, token: str | None = None):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise ImportError(
            "sentence-transformers is required for the similarity stage. "
            "Install it with: pip install sentence-transformers"
        ) from exc
    logger.info(f"Loading embedding model: {model_name} (device=mps)")
    # `token` authenticates the HuggingFace Hub download (higher rate limits,
    # private models). None falls back to anonymous, rate-limited access.
    model = SentenceTransformer(model_name, device="mps", token=token)
    # gte-modernbert-base defaults to 8192 tokens; descriptions are short,
    # so cap at 512 to avoid padding overhead that dominates CPU runtime.
    model.max_seq_length = 512
    return model


def _embed(model, texts: list[str], batch_size: int = 64) -> np.ndarray:
    """Return L2-normalised embeddings of shape (N, dim)."""
    logger.info(f"Encoding {len(texts)} texts (batch_size={batch_size}) ...")
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True,
    )
    return embeddings.astype(np.float32)


def load_embedder(model_name: str, hf_token: str | None = None, batch_size: int = 64):
    """
    Load the model once and return a ``text -> (dim,) float32 vector`` callable.

    The single-record (``enrich-tool``) path embeds one tool against the cached
    corpus. Loading the model is the expensive part, so it is done once here and
    the returned closure is what the incremental service is handed -- which also
    lets tests inject a trivial embedder without any model at all.
    """
    model = _load_model(model_name, token=hf_token)

    def embed_one(text: str) -> np.ndarray:
        return _embed(model, [text], batch_size=batch_size)[0]

    return embed_one


def _top_k_neighbours(
    embeddings: np.ndarray,
    ids: list[str],
    names: list[str],
    k: int,
    chunk_size: int = 1000,
) -> dict[str, dict]:
    """
    Return a dict keyed by tool_id with the top-k most similar tools.

    Cosine similarity equals dot-product when vectors are L2-normalised.
    Processing in row-chunks keeps peak RAM proportional to chunk_size × N
    rather than N × N.
    """
    n = len(embeddings)
    results: dict[str, dict] = {}

    for start in range(0, n, chunk_size):
        end = min(start + chunk_size, n)
        logger.debug(f"Similarity chunk {start}–{end} / {n}")

        # shape: (chunk_size, N)
        slab = np.dot(embeddings[start:end], embeddings.T)

        for local_i, row in enumerate(slab):
            global_i = start + local_i
            row[global_i] = -2.0  # exclude self

            # argpartition is O(N) — much faster than a full sort
            top_idx = np.argpartition(row, -k)[-k:]
            top_idx = top_idx[np.argsort(row[top_idx])[::-1]]

            results[ids[global_i]] = {
                "tool_name": names[global_i],
                "similar": [
                    {
                        "tool_id": ids[j],
                        "tool_name": names[j],
                        "score": round(float(row[j]), 4),
                    }
                    for j in top_idx
                ],
            }

    return results


def compute_similarities(
    tools: list[dict],
    k: int = 10,
    model_name: str = "Alibaba-NLP/gte-modernbert-base",
    batch_size: int = 64,
    chunk_size: int = 1000,
    hf_token: str | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    Embed all tools and return per-tool neighbour documents and their embeddings.

    Parameters
    ----------
    tools:
        Raw MongoDB documents from toolsDev (must contain _id and data fields).
    k:
        Number of nearest neighbours to keep per tool.
    model_name:
        HuggingFace sentence-transformers model identifier.
    batch_size:
        Encoding batch size (tune to GPU/CPU memory).
    chunk_size:
        Row-chunk size for the similarity pass.

    Returns
    -------
    ``(similarity_docs, embedding_records)``:
        - ``similarity_docs``: one dict per tool ready to upsert into
          ``similaritiesDev``.
        - ``embedding_records``: one dict per tool
          (``{tool_id, tool_name, text, vector, version}``) ready to upsert into
          the embedding cache so the per-record ``enrich-tool`` path can reuse
          these vectors instead of re-embedding the corpus.
    """
    if not tools:
        logger.warning("No tools provided — nothing to compute.")
        return [], []

    ids = [str(t["_id"]) for t in tools]
    names = [t.get("data", {}).get("name", "") for t in tools]
    texts = [build_text(t.get("data", {})) for t in tools]
    versions = [t.get("last_updated_at") or t.get("timestamp") for t in tools]

    empty_text_count = sum(1 for tx in texts if not tx)
    if empty_text_count:
        logger.warning(f"{empty_text_count} tools have no description/topics/operations text.")

    model = _load_model(model_name, token=hf_token)
    embeddings = _embed(model, texts, batch_size=batch_size)

    neighbours = _top_k_neighbours(embeddings, ids, names, k=k, chunk_size=chunk_size)

    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    similarity_docs = [
        {
            "tool_id": tool_id,
            "tool_name": info["tool_name"],
            "similar": info["similar"],
            "createdAt": created_at,
        }
        for tool_id, info in neighbours.items()
    ]

    embedding_records = [
        {
            "tool_id": ids[i],
            "tool_name": names[i],
            "text": texts[i],
            "vector": embeddings[i],
            "version": versions[i],
        }
        for i in range(len(ids))
    ]

    return similarity_docs, embedding_records
