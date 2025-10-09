import src.application.services.enrich_publications.europe_pmc as europe_pmc
import src.application.services.enrich_publications.semantic_scholar as semantic_scholar
from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from datetime import datetime
from collections import Counter
import re
import json

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

def enrich_publication_collection():
    """
    Enriches the publication collection with metadata and citations.
    """
    # Fetch all DOIs from the database
    N = 0 

    seen_dois = set()
    with open("scripts/data/publications_enrichment.jsonl", "r") as f:
        # each line is a dict
        for line in f:
            whole_dict = json.loads(line)
            doi = whole_dict.get('doi')
            if doi:
                seen_dois.add(doi.lower())
    
    print(f"Already seen {len(seen_dois)} DOIs")
    

    for doc in mongo_adapter.fetch_entries("publicationsMetadataDev", {"data.doi": {"$exists": True}}):
        N += 1
        id = doc.get("_id")
        doi = doc.get("data", {}).get("doi")

        if doi:
            if doi.lower() in seen_dois:
                 continue
            # Check if DOI is valid
            if not doi.startswith("10."):
                doi = extract_doi(doi)
                if not doi:
                    print(f"DOI extraction failed for: {doi}")
                    continue

            metadata = {}
            # --- Europe PMC -----
            try:
                metadata = europe_pmc.get_publication_metadata(doi)
                metadata = remove_empty_fields(metadata)
                #mongo_adapter.update_entry("publicationsMetadataDev", id, {'data': metadata, 'last_updated_at': datetime.now().strftime("%d/%m/%Y %H:%M:%S") } )
                
                #metadata['source'] = "Europe PMC"
                #with open("scripts/data/publications_enrichment.jsonl", "a") as f:
                #    f.write(json.dumps(metadata) + "\n")

            except Exception as e:
                print(f"Error fetching metadata from Europe PMC for DOI {doi}: {e}")
                
            
            # --- Semantic Scholar -----
            try:
                metadata['doi'] = doi
                citations_sem_scholar = semantic_scholar.fetch_semanticscholar_citations(doi)
                processed_citations = count_citations_per_year(citations_sem_scholar)

                if metadata.get('citations'):
                    metadata['citations'].append({
                        "source": "Semantic Scholar",
                        "count": processed_citations,
                    })
                else:
                    metadata['citations'] = [
                        {
                            "source": "Semantic Scholar",
                            "count": processed_citations,
                        }
                    ]


                metadata = remove_empty_fields(metadata)
                

            except Exception as e:
                print(f"Error fetching metadata from Semantic Scholar for DOI {doi}: {e}")
            
            if metadata:
                mongo_adapter.update_entry("publicationsMetadataDev", id, {'data': metadata, 'last_updated_at': datetime.now().strftime("%d/%m/%Y %H:%M:%S") } )
                
                with open("scripts/data/publications_enrichment.jsonl", "a") as f:
                    f.write(json.dumps(metadata) + "\n")
            else:
                print("No metadata found")

        if N % 1000 == 0:
            print(f"Processed {N} DOIs")

            
            
    




if __name__ == "__main__":
    enrich_publication_collection()