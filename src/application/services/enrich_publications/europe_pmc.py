import requests
from typing import List, Dict

### ------------------- Citations from Europe PMC --------------------------


def parse_metadata(response_dict: Dict, doi: str) -> Dict:
    '''
    Parses the metadata from the response of the Europe PMC API
    Input:
    - response_dict: Dict. The JSON response from the API
    Output:
    - Dict. The parsed metadata
    '''
    metadata = {}
    metadata["doi"] = doi
    if "resultList" in response_dict:
        if "result" in response_dict["resultList"]:
            if len(response_dict["resultList"]["result"]) == 0:
                return {"error": "No results found"}
            else:
                result = response_dict["resultList"]["result"][0]
                result = response_dict["resultList"]["result"][0]
                metadata["title"] = result.get("title", "")
                metadata["abstract"] = result.get("abstractText", "")
                metadata["authors"] = result.get("authorString", "")
                metadata["journal"] = result.get("journalTitle", "")
                metadata["doi"] = result.get("doi", "")
                metadata["pmid"] = result.get("pmid", "")
                metadata["source"] = result.get("source", "")
                metadata["year"] = result.get("pubYear", "")
                metadata["citations"] = [{
                    "source": "Europe PMC",
                    "count": { 'total' : result.get("citedByCount", "")}
                }]
        else:
            return {"error": "No results found"}
    else:
        return {"error": "No results found"}
        
    return metadata


def fetch_metadata(doi: str) -> Dict:
    '''
    Fetches data from Europe PMC using a POST request 
    Input:
    - doi: str. The DOI of the paper
    Output:
    - Dict. The JSON response from the API
    '''
    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/searchPOST"

    # URL-encoded parameters
    payload = {
        "query": f"doi:{doi}",
        "format": "json",
        "resultType": "lite",
        "synonym": "NO"
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    response = requests.post(BASE_URL, data=payload, headers=headers)

    if response.status_code == 200:
        return response.json()
        
        
    else:
        return {"doi": doi, "error": f"Request failed with status code {response.status_code}", "details": response.text}


def get_publication_metadata(doi: str) -> Dict:
    '''
    Fetches metadata from Europe PMC and parses it
    Input:
    - doi: str. The DOI of the paper
    Output:
    - Dict. The metadata of the paper
    '''
    response_json = fetch_metadata(doi)
    return parse_metadata(response_json, doi)


def fetch_citations(identifier: str, source: str) -> List[Dict]:
    '''
    Fetches citations from Europe PMC
    Input:
    - identifier: str. The identifier of the paper
    - source: str. The source of the identifier. Currently, only "pmid" is supported
    Output:
    - List[Dict]. A list of dictionaries containing the citation information
    '''
    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/"
    url = f"{BASE_URL}{source}/{identifier}/citations?format=json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        return data.get("citationList", {}).get("citation", [])
    else:
        return []

import requests

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
        pmid = metadata.get("pmid", "")
        if pmid:
            citations = fetch_citations(pmid, "pmid")
            metadata["citations"] = citations
        return metadata