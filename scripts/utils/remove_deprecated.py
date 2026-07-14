from __future__ import annotations

import argparse

from src.infrastructure.db.mongo.mongo_adapter import MongoDBAdapter

mongo_adapter = MongoDBAdapter()

COLLECTION_NAME = "alambiqueDev"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove documents from alambiqueDev where data.deprecated is true"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show how many documents would be deleted without modifying the database",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    collection = mongo_adapter.get_collection(COLLECTION_NAME)
    query = {"data.deprecated": True}

    count = collection.count_documents(query)
    print(f"Found {count} deprecated documents in {COLLECTION_NAME}")

    if args.dry_run:
        print("Dry run enabled. No changes were made.")
        return

    result = collection.delete_many(query)
    print(f"Deleted {result.deleted_count} documents from {COLLECTION_NAME}")


if __name__ == "__main__":
    main()