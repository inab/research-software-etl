from infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


def get_citation_sources(doc: dict) -> set[str]:
    """
    Extract citation sources from a publication document.
    """
    citations = doc.get("data", {}).get("citations", [])

    if not isinstance(citations, list):
        return set()

    sources = set()
    for citation in citations:
        if not isinstance(citation, dict):
            continue

        source = citation.get("source")
        if isinstance(source, str):
            sources.add(source.strip())

    return sources


def get_publication_count(tool: dict) -> int:
    """
    Return the number of publication ids linked from a tool document.
    """
    publications = tool.get("data", {}).get("publication", [])

    if publications is None:
        return 0

    if isinstance(publications, str):
        publications = [publications]

    if not isinstance(publications, list):
        return 0

    valid_publications = [pub for pub in publications if isinstance(pub, str) and pub.strip()]
    return len(valid_publications)


if __name__ == "__main__":
    total_docs = 0
    semantic_scholar_count = 0
    europe_pmc_count = 0
    both_count = 0

    tools_with_publications = 0
    total_linked_publications = 0

    for doc in mongo_adapter.fetch_entries("publicationsMetadataDev", {}):
        total_docs += 1
        sources = get_citation_sources(doc)

        has_semantic_scholar = "Semantic Scholar" in sources
        has_europe_pmc = "Europe PMC" in sources

        if has_semantic_scholar:
            semantic_scholar_count += 1

        if has_europe_pmc:
            europe_pmc_count += 1

        if has_semantic_scholar and has_europe_pmc:
            both_count += 1

    for tool in mongo_adapter.fetch_entries("toolsDev", {}):
        publication_count = get_publication_count(tool)

        if publication_count > 0:
            tools_with_publications += 1
            total_linked_publications += publication_count

    print(f"Total publication docs: {total_docs}")
    print(f"Publication docs with Semantic Scholar counts: {semantic_scholar_count}")
    print(f"Publication docs with Europe PMC counts: {europe_pmc_count}")
    print(f"Publication docs with both Semantic Scholar and Europe PMC counts: {both_count}")
    print(f"Tools with publications: {tools_with_publications}")
    print(f"Total linked publications in toolsDev: {total_linked_publications}")