from infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from application.services.post_transformation.normalize_tool_licenses import (
    normalize_tool_licenses,
)


def update_toolsdev_licenses():
    """
    Map toolsDev licenses to SPDX when possible, add SPDX URLs, remove duplicates,
    and persist the normalized license list back to MongoDB.
    """
    total = 0
    updated = 0
    unchanged = 0
    errors = 0

    for tool in mongo_adapter.fetch_entries("toolsDev", {}):
        total += 1

        try:
            tool_id = tool["_id"]
            current_licenses = tool.get("data", {}).get("license", [])
            normalized_licenses = normalize_tool_licenses(tool)

            if current_licenses == normalized_licenses:
                unchanged += 1
                continue

            mongo_adapter.update_entry(
                "toolsDev",
                tool_id,
                {"data.license": normalized_licenses},
            )
            updated += 1

        except Exception as e:
            errors += 1
            print(f"Error processing tool {tool.get('_id')}: {e}")

    print(f"Total tools processed: {total}")
    print(f"Updated docs: {updated}")
    print(f"Unchanged docs: {unchanged}")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    update_toolsdev_licenses()