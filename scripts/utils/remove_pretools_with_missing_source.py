from __future__ import annotations

import argparse
import random

from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter

PRETOOLS_COLLECTION = "pretoolsDev"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Remove documents from pretoolsDev whose single source document "
            "does not exist."
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without modifying the database",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit of pretools documents to inspect",
    )
    parser.add_argument(
        "--sanity-check-size",
        type=int,
        default=5,
        help="Number of random positive-control documents to test",
    )
    return parser.parse_args()


def get_source_ref(doc: dict) -> dict | None:
    sources = doc.get("source", [])
    if not isinstance(sources, list) or len(sources) != 1:
        return None

    source_ref = sources[0]
    if not isinstance(source_ref, dict):
        return None

    return source_ref


def source_exists(source_ref: dict) -> bool:
    collection_name = source_ref.get("collection")
    source_id = source_ref.get("id")

    if not collection_name or not source_id:
        return False

    source_col = mongo_adapter.get_collection(collection_name)
    source_doc = source_col.find_one({"_id": source_id}, {"_id": 1})
    return source_doc is not None


def run_positive_control(pretools_docs: list[dict], sanity_check_size: int) -> None:
    candidates = []

    for doc in pretools_docs:
        source_ref = get_source_ref(doc)
        if not source_ref:
            continue
        if source_exists(source_ref):
            candidates.append((doc, source_ref))

    print(f"Positive-control candidates with retrievable source: {len(candidates)}")

    if not candidates:
        print(
            "WARNING: no positive-control candidates found. "
            "This suggests source retrieval may not be working as expected."
        )
        return

    sample_size = min(sanity_check_size, len(candidates))
    sampled = random.sample(candidates, sample_size)

    print(f"\nPositive control: checking {sample_size} random retrievable sources\n")

    for doc, source_ref in sampled:
        print("=" * 100)
        print(f"PRETOOL ID: {doc.get('_id')}")
        print(f"SOURCE COLLECTION: {source_ref.get('collection')}")
        print(f"SOURCE ID: {source_ref.get('id')}")
        print("RESULT: source document successfully retrieved")


def main() -> None:
    args = parse_args()

    pretools_col = mongo_adapter.get_collection(PRETOOLS_COLLECTION)

    cursor = pretools_col.find(
        {},
        {
            "_id": 1,
            "id": 1,
            "source": 1,
            "name": 1,
        },
    )

    pretools_docs = list(cursor)

    if args.limit is not None:
        pretools_docs = pretools_docs[: args.limit]

    print(f"Loaded {len(pretools_docs)} documents from {PRETOOLS_COLLECTION}")

    # Positive control first
    run_positive_control(pretools_docs, args.sanity_check_size)

    docs_to_delete = []
    skipped_bad_source_shape = 0

    for doc in pretools_docs:
        source_ref = get_source_ref(doc)

        if source_ref is None:
            skipped_bad_source_shape += 1
            continue

        if not source_exists(source_ref):
            docs_to_delete.append(
                {
                    "_id": doc["_id"],
                    "id": doc.get("id"),
                    "source_collection": source_ref.get("collection"),
                    "source_id": source_ref.get("id"),
                }
            )

    print("\n" + "=" * 100)
    print(f"Docs with malformed or missing single-source structure skipped: {skipped_bad_source_shape}")
    print(f"pretools docs whose source document does not exist: {len(docs_to_delete)}")

    preview_size = min(10, len(docs_to_delete))
    if preview_size:
        print(f"\nPreview of first {preview_size} docs to delete:\n")
        for item in docs_to_delete[:preview_size]:
            print("=" * 100)
            print(f"PRETOOL _ID: {item['_id']}")
            print(f"PRETOOL ID: {item.get('id')}")
            print(f"SOURCE COLLECTION: {item['source_collection']}")
            print(f"MISSING SOURCE ID: {item['source_id']}")

    if args.dry_run:
        print("\nDry run enabled. No changes were made.")
        return

    if not docs_to_delete:
        print("\nNothing to delete.")
        return

    ids_to_delete = [item["_id"] for item in docs_to_delete]
    result = pretools_col.delete_many({"_id": {"$in": ids_to_delete}})

    print("\nDeletion completed.")
    print(f"Deleted {result.deleted_count} documents from {PRETOOLS_COLLECTION}")


if __name__ == "__main__":
    main()