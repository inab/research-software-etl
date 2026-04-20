from collections import Counter

from infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


TARGET_TAG = "Proteomics"


def normalize_string_list(value) -> list[str]:
    """
    Normalize a field that may contain:
    - None
    - a single string
    - a list of strings
    """
    if value is None:
        return []

    if isinstance(value, str):
        value = [value]

    if not isinstance(value, list):
        return []

    normalized = []
    for item in value:
        if isinstance(item, str):
            item = item.strip()
            if item:
                normalized.append(item)

    return normalized


def has_target_tag(tool: dict, target_tag: str) -> bool:
    """
    Return True if data.tags contains the target tag.
    """
    tags = normalize_string_list(tool.get("data", {}).get("tags", []))
    return target_tag in tags


def get_sources(tool: dict) -> list[str]:
    """
    Return normalized sources from data.source.
    """
    return normalize_string_list(tool.get("data", {}).get("source", []))


def is_exclusive_biotools(tool: dict) -> bool:
    """
    Return True if the tool comes exclusively from biotools,
    i.e. data.source is exactly ['biotools'] after normalization.
    """
    sources = get_sources(tool)
    return sources == ["biotools"]


def has_publications(tool: dict) -> bool:
    """
    Return True if data.publication contains at least one non-empty string.
    """
    publications = normalize_string_list(tool.get("data", {}).get("publication", []))
    return len(publications) > 0


def has_documentation(tool: dict) -> bool:
    """
    Return True if data.documentation is a non-empty list.
    """
    documentation = tool.get("data", {}).get("documentation", [])
    return isinstance(documentation, list) and len(documentation) > 0


def has_test(tool: dict) -> bool:
    """
    Return True if data.test is exactly True.
    """
    return tool.get("data", {}).get("test") is True


def has_downloads(tool: dict) -> bool:
    """
    Return True if data.download contains at least one non-empty string.
    """
    downloads = normalize_string_list(tool.get("data", {}).get("download", []))
    return len(downloads) > 0


def pct(part: int, total: int) -> float:
    """
    Return percentage rounded to 2 decimals.
    """
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)


if __name__ == "__main__":
    total_docs = 0
    source_counts = Counter()
    docs_with_publications = 0
    docs_with_documentation = 0
    docs_with_test_true = 0
    docs_with_downloads = 0
    docs_exclusive_biotools = 0

    for tool in mongo_adapter.fetch_entries("toolsDev", {}):
        if not has_target_tag(tool, TARGET_TAG):
            continue

        total_docs += 1

        sources = get_sources(tool)
        for source in set(sources):
            source_counts[source] += 1

        if is_exclusive_biotools(tool):
            docs_exclusive_biotools += 1

        if has_publications(tool):
            docs_with_publications += 1

        if has_documentation(tool):
            docs_with_documentation += 1

        if has_test(tool):
            docs_with_test_true += 1

        if has_downloads(tool):
            docs_with_downloads += 1

    print(f"Tag: {TARGET_TAG}")
    print(f"Total number of docs: {total_docs}")
    print(
        f"Number of tools coming exclusively from biotools: "
        f"{docs_exclusive_biotools} ({pct(docs_exclusive_biotools, total_docs)}%)"
    )
    print("Number of docs extracted from each source:")

    for source, count in source_counts.most_common():
        print(f"  - {source}: {count} ({pct(count, total_docs)}%)")

    print(
        f"Number of docs with publications: "
        f"{docs_with_publications} ({pct(docs_with_publications, total_docs)}%)"
    )
    print(
        f"Number of docs with documentation: "
        f"{docs_with_documentation} ({pct(docs_with_documentation, total_docs)}%)"
    )
    print(
        f"Number of docs with test == True: "
        f"{docs_with_test_true} ({pct(docs_with_test_true, total_docs)}%)"
    )
    print(
        f"Number of docs with downloads: "
        f"{docs_with_downloads} ({pct(docs_with_downloads, total_docs)}%)"
    )