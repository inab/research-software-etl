import src.application.services.enrich_publications.europe_pmc as europe_pmc
import src.application.services.enrich_publications.semantic_scholar as semantic_scholar
from collections import Counter
import re

def extract_doi(url: str) -> str | None:
    """
    Extracts the DOI from a DOI URL.

    Args:
        url (str): The URL containing the DOI.

    Returns:
        str | None: The extracted DOI string, or None if not found.
    """
    # DOI pattern: starts with 10. followed by a digit and any characters except spaces
    doi_pattern = re.compile(r'10\.\d{4,9}/[^\s"<>]+', re.IGNORECASE)

    match = doi_pattern.search(url)
    return match.group(0) if match else None


def get_metadata_and_citations_semantic_scholar(doi):
    '''
    Fetches metadata from Europe PMC and adds citations if available
    Input:
    - doi: str. The DOI of the paper
    Output:
    - Dict. The metadata of the paper with citations added
    '''
    metadata = semantic_scholar.get_publication_metadata(doi)
    if "error" in metadata:
        return metadata
    else:
        citations = semantic_scholar.fetch_semanticscholar_citations(doi)
        metadata["citations"] = citations
        return metadata
    
def count_citations_per_year(data):
    """
    Given a Semantic Scholar citation data dictionary, return a dictionary
    with citation counts per year.
    """
    year_counts = Counter()
    for entry in data.get("data", []):
        paper = entry.get("citingPaper", {})
        year = paper.get("year")
        if year is not None:
            year_counts[f'{year}'] += 1

    year_counts['total'] = sum(year_counts.values())
    return dict(year_counts)


def get_europe_pmc_metadata(doi):
    metadata = europe_pmc.get_publication_metadata(doi)

    if "error" not in metadata:
        metadata['citations'] = [metadata["citations"]]

    else:
        metadata = {
            'doi': doi,
            'citations': []
        }
    
    return metadata

def remove_empty_fields(d: dict) -> dict:
    """
    Recursively remove keys with empty values from a dict.
    Empty values are: None, '', [], {}, and only-whitespace strings.
    """
    if not isinstance(d, dict):
        return d

    cleaned = {}
    for k, v in d.items():
        if isinstance(v, dict):
            v = remove_empty_fields(v)
        elif isinstance(v, list):
            v = [remove_empty_fields(i) if isinstance(i, dict) else i for i in v]
            v = [i for i in v if i not in (None, '', [], {})]

        # Keep only non-empty values
        if v not in (None, '', [], {}) and not (isinstance(v, str) and v.strip() == ''):
            cleaned[k] = v

    return cleaned

