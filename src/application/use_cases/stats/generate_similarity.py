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

from application.services.stats_generation.similarity.compute_embeddings import compute_similarities
from domain.repositories import Repositories

logger = logging.getLogger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def compute_and_store_similarities(
    repos: Repositories,
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
    if not force and not repos.similarities.is_empty():
        logger.info("Similarities already computed. Pass --force to recompute.")
        print("[SKIP] The similarities collection is already populated. Use --force to recompute.")
        return

    # The front-end fetches neighbours by tool_id, and the upsert below assumes one
    # document per tool.
    repos.similarities.ensure_tool_id_index()

    query = {} if tag_or_tools == "tools" else {"data.tags": tag_or_tools}
    logger.info(f"Fetching tools (query={query}) ...")
    tools = list(repos.tools.find(query))
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
        try:
            repos.similarities.upsert_by_tool_id(doc)
            upserted += 1
        except Exception as exc:
            failed += 1
            logger.error(f"[FAIL] tool_id={doc['tool_id']}: {exc}")

    print(f"\nDone. upserted={upserted}, failed={failed}")
