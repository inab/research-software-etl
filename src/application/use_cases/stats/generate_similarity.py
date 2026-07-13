"""
Use case: compute and persist tool-similarity scores in MongoDB.

Reads all tools from toolsDev, embeds their descriptions, computes pairwise
cosine similarity, and stores the top-k nearest neighbours per tool in the
similaritiesDev collection so the front-end can fetch them by tool_id.

Behaviour:
- If similaritiesDev is already populated and force=False, the run is skipped.
- Use force=True to recompute and replace all existing documents.

---> Re-run whenever the tools collection changes significantly.
"""

import logging
from datetime import datetime, timezone

from infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from application.services.stats_generation.similarity.compute_embeddings import compute_similarities

logger = logging.getLogger(__name__)

TOOLS_COLLECTION = "toolsDev"
SIMILARITY_COLLECTION = "similaritiesDev"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _collection_is_populated() -> bool:
    existing = mongo_adapter.fetch_entry(SIMILARITY_COLLECTION, {})
    return existing is not None


def compute_and_store_similarities(
    tag_or_tools: str = "tools",
    k: int = 10,
    force: bool = False,
    model_name: str = "Alibaba-NLP/gte-modernbert-base",
    batch_size: int =64,
    chunk_size: int = 1000,
) -> None:
    """
    Compute pairwise similarity and upsert results into similaritiesDev.

    Parameters
    ----------
    tag_or_tools:
        "tools" to process all tools, or a tag value to filter by data.tags.
    k:
        Number of nearest neighbours to store per tool.
    force:
        If True, recompute even when the collection already has data.
    model_name:
        Sentence-transformers model to use for embedding.
    batch_size:
        Encoding batch size.
    chunk_size:
        Row-chunk size for the similarity slab computation.
    """
    if not force and _collection_is_populated():
        logger.info(
            f"{SIMILARITY_COLLECTION} already contains data. "
            "Pass --force to recompute."
        )
        print(
            f"[SKIP] {SIMILARITY_COLLECTION} is already populated. "
            "Use --force to recompute."
        )
        return

    # Ensure a unique index on tool_id for efficient front-end lookups
    try:
        mongo_adapter.get_collection(SIMILARITY_COLLECTION).create_index(
            "tool_id", unique=True
        )
    except Exception as exc:
        logger.warning(f"Could not create index on tool_id: {exc}")

    query = {} if tag_or_tools == "tools" else {"data.tags": tag_or_tools}
    logger.info(f"Fetching tools from {TOOLS_COLLECTION} (query={query}) ...")
    tools = list(mongo_adapter.fetch_entries(TOOLS_COLLECTION, query))
    logger.info(f"Fetched {len(tools)} tools.")

    if not tools:
        print("[SKIP] No tools found.")
        return

    print(f"[INFO] Computing similarities for {len(tools)} tools (k={k}) ...")
    similarity_docs = compute_similarities(
        tools,
        k=k,
        model_name=model_name,
        batch_size=batch_size,
        chunk_size=chunk_size,
    )

    upserted = 0
    failed = 0
    for doc in similarity_docs:
        match = {"tool_id": doc["tool_id"]}
        try:
            mongo_adapter.update_custom_upsert(SIMILARITY_COLLECTION, match, doc)
            upserted += 1
        except Exception as exc:
            failed += 1
            logger.error(f"[FAIL] tool_id={doc['tool_id']}: {exc}")

    print(f"\nDone. upserted={upserted}, failed={failed}")
