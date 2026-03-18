from __future__ import annotations

from typing import Any
import requests


class EuropePmcClient:
    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/searchPOST"

    def parse_metadata(self, response_dict: dict[str, Any], doi: str) -> dict[str, Any]:
        """
        Parse Europe PMC metadata response.
        """
        metadata: dict[str, Any] = {"doi": doi}

        if "resultList" not in response_dict:
            return {"doi": doi, "error": "No results found"}

        if "result" not in response_dict["resultList"]:
            return {"doi": doi, "error": "No results found"}

        results = response_dict["resultList"]["result"]
        if len(results) == 0:
            return {"doi": doi, "error": "No results found"}

        result = results[0]
        metadata["title"] = result.get("title", "")
        metadata["abstract"] = result.get("abstractText", "")
        metadata["authors"] = result.get("authorString", "")
        metadata["journal"] = result.get("journalTitle", "")
        metadata["doi"] = result.get("doi", doi)
        metadata["pmid"] = result.get("pmid", "")
        metadata["source"] = result.get("source", "")
        metadata["year"] = result.get("pubYear", "")
        metadata["citations"] = [
            {
                "source": "Europe PMC",
                "count": {"total": result.get("citedByCount", "")},
            }
        ]
        return metadata

    def fetch_metadata(self, doi: str) -> dict[str, Any]:
        """
        Fetch metadata from Europe PMC using POST.
        """
        payload = {
            "query": f"doi:{doi}",
            "format": "json",
            "resultType": "lite",
            "synonym": "NO",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        response = requests.post(
            self.BASE_URL,
            data=payload,
            headers=headers,
            timeout=30,
        )

        if response.status_code == 200:
            return response.json()

        return {
            "doi": doi,
            "error": f"Request failed with status code {response.status_code}",
            "details": response.text,
        }

    def get_publication_metadata(self, doi: str) -> dict[str, Any]:
        response_json = self.fetch_metadata(doi)
        return self.parse_metadata(response_json, doi)

    def fetch_citations(self, identifier: str, source: str) -> list[dict[str, Any]]:
        """
        Fetch citations from Europe PMC by identifier/source.
        Example: source='pmid'
        """
        base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/"
        url = f"{base_url}{source}/{identifier}/citations?format=json"

        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data.get("citationList", {}).get("citation", [])

        return []

    def get_metadata_and_citations(self, doi: str) -> dict[str, Any]:
        """
        Preserve the old combined behavior.
        """
        metadata = self.get_publication_metadata(doi)
        if "error" in metadata:
            return metadata

        pmid = metadata.get("pmid", "")
        if pmid:
            citations = self.fetch_citations(pmid, "pmid")
            metadata["citations"] = citations

        return metadata