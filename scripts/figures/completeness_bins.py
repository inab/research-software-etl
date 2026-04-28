from typing import Dict, Any
from infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


def is_value_meaningful(value: Any) -> bool:
    """
    Check if a value is meaningful (not None, empty, or 'unknown').
    """
    if value in [None, "", "None", "unknown", False]:
        return False
    if value is True:
        return True
    if isinstance(value, list):
        return any(is_value_meaningful(v) for v in value)
    return True


def is_meaningful(key, value, features):
    if key in features:
        if value in [None, "", "None", "unknown", False]:
            return False
        if isinstance(value, list):
            return any(is_value_meaningful(v) for v in value)
        return True
    return False


def completeness(records, features):
    def count_features(tool: Dict[str, Any]) -> float:
        return sum(1 for k, v in tool.items() if is_meaningful(k, v, features)) / len(features)

    completeness_percentages = [count_features(record["data"]) for record in records]
    return completeness_percentages


software_features = [
    "name",
    "type",
    "version",
    "label",
    "description",
    "source_code",
    "download",
    "license",
    "documentation",
    "operating_system",
    "repository",
    "webpage",
    "input",
    "output",
    "dependencies",
    "authors",
    "publication",
    "topics",
    "operations",
    "test",
]

publication_features = [
    "year",
    "title",
    "journal",
    "authors",
    "pmid",
    "doi",
]


def bin_scores_by_completeness(scores, bin_size=700):
    """
    Given a list of completeness scores (floats from 0 to 1),
    sort them and return average completeness per bin.

    Parameters:
        scores: list of float values
        bin_size: number of records per bin

    Returns:
        List of average completeness scores per bin
    """
    sorted_scores = sorted(scores)
    bins = []
    for i in range(0, len(sorted_scores), bin_size):
        chunk = sorted_scores[i:i + bin_size]
        avg = sum(chunk) / len(chunk) if chunk else 0
        bins.append(avg)
    return bins


def software_completeness():
    sources = ["bioconda_recipes", "bioconductor", "biotools", "github", "sourceforge", "galaxy", "toolshed"]
    for source in sources:
        records = mongo_adapter.fetch_entries("toolsDev", {"data.source": source})
        n = 0
        n_calculated = n
        percentages = []
        print(f"Extracted {len(records)} records from {source} source")

        for record in records:
            n += 1
            subrecords_completeness = []
            source_ids = [
                pretools_id
                for pretools_id in record["source"]
                if f"{source}/" in pretools_id
            ]
            if source_ids:
                for source_id in source_ids:
                    sub_record = mongo_adapter.fetch_entry("pretoolsDev", {"_id": source_id})
                    if sub_record:
                        record_completeness = completeness([sub_record], software_features)
                        n_calculated += 1
                        subrecords_completeness.append(record_completeness[0])

            if subrecords_completeness:
                completeness_score = sum(subrecords_completeness) / len(subrecords_completeness)
                percentages.append(completeness_score)

        bins = bin_scores_by_completeness(percentages)

        print(f" ----- Bins for {source} ----- ")
        for i, score in enumerate(bins):
            print(f"Bin {i}: {score * 100:.3f}%")

        print("-----------------------------------")


def software_completeness_total():
    source = "tools"
    records = mongo_adapter.fetch_entries("toolsDev", {})

    n = 0
    n_calculated = n
    percentages = []
    print(f"Extracted {len(records)} records from {source} source")

    for record in records:
        n += 1
        record_completeness = completeness([record], software_features)
        n_calculated += 1
        percentages.append(record_completeness[0])

    bins = bin_scores_by_completeness(percentages)

    print(f" ----- Bins for {source} ----- ")
    for i, score in enumerate(bins):
        print(f"Bin {i}: {score * 100:.2f}%")

    print("-----------------------------------")


def publications_completeness():
    records = mongo_adapter.fetch_entries("publicationsMetadataDev", {})
    pubs_perct = []

    def count_features(tool: Dict[str, Any]) -> int:
        return sum(1 for k, v in tool.items() if is_meaningful(k, v, publication_features))

    for record in records:
        features_count = count_features(record["data"])

        if record["data"].get("citations"):
            for item in record["data"]["citations"]:
                if not item.get("source"):
                    continue

                if item["source"] == "Europe PMC":
                    features_count += 1

        if features_count == 0:
            #print("Record with cero features")
            pass

        percentage_record = features_count / 7
        pubs_perct.append(percentage_record)

    bins = bin_scores_by_completeness(pubs_perct)
    print(" ----- Bins for publications ----- ")
    print(f"Extracted {len(records)} records from publications")
    for i, score in enumerate(bins):
        print(f"Bin {i}: {score * 100:.4f}%")
    print("-----------------------------------")


def pubs_sources_completeness():
    """
    Compute completeness bins for publication information coming from
    Europe PMC, using publications_metadata.

    Assumptions:
    - Publication metadata live in the "data" field of each document.
    - Source-specific citation info is stored in data.citations as a list of dicts.
    - Europe PMC records are publication docs that contain a citation entry
      with source == "Europe PMC".
    """

    def count_features(publication_data: Dict[str, Any]) -> int:
        return sum(
            1
            for k, v in publication_data.items()
            if is_meaningful(k, v, publication_features)
        )

    def get_citation_entry_by_source(publication_data: Dict[str, Any], source_name: str):
        citations = publication_data.get("citations", [])

        if not isinstance(citations, list):
            return None

        for citation in citations:
            if not isinstance(citation, dict):
                continue
            if citation.get("source") == source_name:
                return citation

        return None

    europe_pmc = []

    for doc in mongo_adapter.fetch_entries("publications_metadata", {}):
        publication_data = doc.get("data", {})

        if not isinstance(publication_data, dict):
            continue

        europe_pmc_citation = get_citation_entry_by_source(publication_data, "Europe PMC")

        if europe_pmc_citation is not None:
            europe_pmc.append(publication_data)

    perc_europe_pmc = []
    for record in europe_pmc:
        features_count = count_features(record)
        percentage_record = features_count / 7
        perc_europe_pmc.append(percentage_record)

    bins = bin_scores_by_completeness(perc_europe_pmc)
    print(" ----- Bins for Europe PMC ----- ")
    print(f"Extracted {len(europe_pmc)} records from Europe PMC")
    for i, score in enumerate(bins):
        print(f"Bin {i}: {score * 100:.4f}%")
    print("-----------------------------------")


if __name__ == "__main__":
    publications_completeness()
    #software_completeness()
    #software_completeness_total()
    #pubs_sources_completeness()