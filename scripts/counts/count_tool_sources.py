from collections import Counter

from infrastructure.db.mongo.mongo_adapter import MongoDBAdapter

mongo_adapter = MongoDBAdapter()


def normalize_sources(tool: dict) -> list[str]:
    """
    Return data.source as a normalized list of strings.

    Handles:
    - missing field
    - a single string
    - a list of strings
    """
    sources = tool.get("data", {}).get("source", [])

    if sources is None:
        return []

    if isinstance(sources, str):
        sources = [sources]

    if not isinstance(sources, list):
        return []

    normalized = []
    for source in sources:
        if isinstance(source, str):
            source = source.strip()
            if source:
                normalized.append(source)

    return normalized


if __name__ == "__main__":
    total_tools = 0
    total_pretools = 0
    source_counts = Counter()
    tools_without_source = 0

    for _ in mongo_adapter.fetch_entries("pretoolsDev", {}):
        total_pretools += 1

    for tool in mongo_adapter.fetch_entries("toolsDev", {}):
        total_tools += 1
        sources = normalize_sources(tool)

        if not sources:
            tools_without_source += 1
            continue

        # Count each source once per document
        for source in set(sources):
            source_counts[source] += 1

    print(f"pretools_total: {total_pretools}")
    print(f"total: {total_tools}")

    for source, count in source_counts.most_common():
        print(f"{source}: {count}")

    print(f"without_source: {tools_without_source}")