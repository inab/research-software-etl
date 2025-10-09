import requests
from typing import Dict

# ---------------------- SEMANTIC SCHOLAR ----------------------

# Docs: https://api.semanticscholar.org/api-docs/


def parse_metadata(response_dict, doi):
    """
    Parses the metadata from the response of the Semantic Scholar API.
    
    Input:
        response_dict (dict): The JSON response from the API.
        doi (str): The DOI of the paper.
    
    Output:
        dict: The parsed metadata.
    """
    metadata = {"doi": doi}
    metadata["title"] = response_dict.get("title", "")
    metadata["abstract"] = response_dict.get("abstract", "")
    metadata["authors"] = ", ".join([author.get("name", "") for author in response_dict.get("authors", [])])
    metadata["journal"] = response_dict.get("journal", {}).get("name", "")
    metadata["pmid"] = response_dict.get("externalIds", {}).get("PubMed", "")
    metadata["source"] = response_dict.get("source", "")
    metadata["year"] = response_dict.get("year", "")
    metadata["citations"] = [{
        "source": "Semantic Scholar",
        "count": response_dict.get("citationCount", "")
    }]

    return metadata
    


def fetch_metadata(doi):
    """
    Fetches metadata for a paper using its DOI from the Semantic Scholar API.
    
    Input:
        doi (str): The DOI of the paper.
    
    Output:
        dict: A dictionary containing the paper's metadata.
    """
    base_url = "https://api.semanticscholar.org/graph/v1/paper/DOI:"
    fields = "paperId,title,abstract,year,venue,journal,fieldsOfStudy,authors,citationCount,references,citations,isOpenAccess,openAccessPdf,embedding,tldr,s2FieldsOfStudy,externalIds,url"
    url = f"{base_url}{doi}?fields={fields}"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Failed to fetch data, Status Code: {response.status_code}"}

def get_publication_metadata(doi: str) -> Dict:
    """
    Fetches metadata for a publication using its DOI from the Semantic Scholar API.
    
    Input:
        doi (str): The DOI of the publication.
    
    Output:
        dict: A dictionary containing the publication's metadata.
    """
    response = fetch_metadata(doi)
    return parse_metadata(response, doi)


def fetch_semanticscholar_citations(doi):
    url = f"https://api.semanticscholar.org/graph/v1/paper/{doi}/citations?fields=paperId,title,year"
    response = requests.get(url)

    if response.status_code == 200:
        return response.json()
    else:
        return {"error": f"Request failed with status code {response.status_code}", "details": response.text}

def get_metadata_and_citations(doi):
    '''
    Fetches metadata from Europe PMC and adds citations if available
    Input:
    - doi: str. The DOI of the paper
    Output:
    - Dict. The metadata of the paper with citations added
    '''
    metadata = get_publication_metadata(doi)
    if "error" in metadata:
        return metadata
    else:
        citations = fetch_semanticscholar_citations(doi)
        metadata["citations"] = citations
        return metadata
    