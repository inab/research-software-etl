 # Count reords in tools with type web, rest, sparql, workbench or suite 

from infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


TARGET_TYPES = {"web", "rest", "sparql", "workbench", "suite"}


def normalize_types(tool: dict) -> list[str]:
    """
    Return the tool types as a normalized list of lowercase strings.
    """
    types = tool.get("data", {}).get("type", [])

    if types is None:
        return []

    if isinstance(types, str):
        types = [types]

    if not isinstance(types, list):
        return []

    normalized = []
    for t in types:
        if isinstance(t, str):
            normalized.append(t.strip().lower())

    return normalized


if __name__ == "__main__":
    deployable = 0
    counts_by_type = {t: 0 for t in TARGET_TYPES}

    for tool in mongo_adapter.fetch_entries("toolsDev", {}):
        tool_types = normalize_types(tool)
        matched_types = set(tool_types) & TARGET_TYPES

        if matched_types:
            deployable += 1
            for matched_type in matched_types:
                counts_by_type[matched_type] += 1

    print(f"Tools with at least one deployable type: {deployable}")
    print("Breakdown by type:")

    for type_name in sorted(counts_by_type):
        print(f"  - {type_name}: {counts_by_type[type_name]}")