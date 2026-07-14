from __future__ import annotations

import argparse

from infrastructure.db.mongo.mongo_adapter import MongoDBAdapter

mongo_adapter = MongoDBAdapter()

PUBLICATIONS_COLLECTION = "publicationsMetadataDev"
TOOLS_COLLECTION = "toolsDev"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Remove bad publication docs (no title and no DOI) and "
            "remove their ids from toolsDev.data.publication"
        )
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying the database",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit of bad publication docs to process",
    )
    return parser.parse_args()


def get_bad_publications_query() -> dict:
    return {
        "$and": [
            {
                "$or": [
                    {"data.title": {"$exists": False}},
                    {"data.title": None},
                    {"data.title": ""},
                ]
            },
            {
                "$or": [
                    {"data.doi": {"$exists": False}},
                    {"data.doi": None},
                    {"data.doi": ""},
                ]
            },
        ]
    }


def main() -> None:
    args = parse_args()

    publications_col = mongo_adapter.get_collection(PUBLICATIONS_COLLECTION)
    tools_col = mongo_adapter.get_collection(TOOLS_COLLECTION)

    bad_publications_query = get_bad_publications_query()

    bad_publications_cursor = publications_col.find(
        bad_publications_query,
        {
            "_id": 1,
            "data.title": 1,
            "data.doi": 1,
        },
    )

    bad_publications = list(bad_publications_cursor)

    if args.limit is not None:
        bad_publications = bad_publications[: args.limit]

    bad_publication_ids = [doc["_id"] for doc in bad_publications]
    bad_publication_id_strs = [str(doc["_id"]) for doc in bad_publications]
    bad_publications_by_id_str = {str(doc["_id"]): doc for doc in bad_publications}

    print(f"Found {len(bad_publication_ids)} bad publication docs")

    if not bad_publication_ids:
        print("Nothing to do.")
        return

    bad_tools_query = {
        "data.publication": {"$in": bad_publication_id_strs}
    }

    bad_matching_tools = list(
        tools_col.find(
            bad_tools_query,
            {
                "_id": 1,
                "data.name": 1,
                "data.url": 1,
                "data.publication": 1,
            },
        )
    )

    print(f"Found {len(bad_matching_tools)} tools linked to bad publications")

    tool_updates = []
    total_removed_references = 0

    for tool in bad_matching_tools:
        tool_id = tool["_id"]
        tool_data = tool.get("data", {})
        current_publications = tool_data.get("publication", [])

        if not isinstance(current_publications, list):
            print(
                f"Skipping tool {tool_id} because data.publication is not a list: "
                f"{type(current_publications)}"
            )
            continue

        removed_ids = [
            pub_id for pub_id in current_publications if pub_id in bad_publications_by_id_str
        ]
        new_publications = [
            pub_id for pub_id in current_publications if pub_id not in bad_publications_by_id_str
        ]

        if not removed_ids:
            continue

        total_removed_references += len(removed_ids)
        tool_updates.append(
            {
                "tool_id": tool_id,
                "tool_name": tool_data.get("name"),
                "tool_url": tool_data.get("url"),
                "removed_ids": removed_ids,
                "new_publications": new_publications,
            }
        )

    print(f"Tools that will be updated: {len(tool_updates)}")
    print(f"Total bad publication references to remove: {total_removed_references}")
    print(f"Bad publication docs to delete: {len(bad_publication_ids)}")

    preview_count = min(10, len(tool_updates))
    if preview_count:
        print(f"\nPreview of first {preview_count} tool updates:")
        for update in tool_updates[:preview_count]:
            print("\n" + "=" * 100)
            print(f"TOOL ID: {update['tool_id']}")
            print(f"TOOL NAME: {update['tool_name']}")
            print(f"TOOL URL: {update['tool_url']}")
            print(f"REMOVED REFERENCES: {len(update['removed_ids'])}")
            for pub_id in update["removed_ids"][:10]:
                pub = bad_publications_by_id_str.get(pub_id, {})
                data = pub.get("data", {})
                print(
                    f"  - PUB ID: {pub_id} | "
                    f"TITLE: {data.get('title')} | DOI: {data.get('doi')}"
                )

    if args.dry_run:
        print("\nDry run enabled. No changes were made.")
        return

    updated_tools = 0
    for update in tool_updates:
        tools_col.update_one(
            {"_id": update["tool_id"]},
            {"$set": {"data.publication": update["new_publications"]}},
        )
        updated_tools += 1

    delete_result = publications_col.delete_many(
        {"_id": {"$in": bad_publication_ids}}
    )

    print("\nCleanup completed.")
    print(f"Updated tools: {updated_tools}")
    print(f"Deleted publications: {delete_result.deleted_count}")


if __name__ == "__main__":
    main()