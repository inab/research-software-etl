from __future__ import annotations

from typing import Any
import requests


class SemanticScholarClient:
    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def parse_metadata(self, response_dict: dict[str, Any], doi: str) -> dict[str, Any]:
        metadata = {"doi": doi}
        metadata["title"] = response_dict.get("title", "")
        metadata["abstract"] = response_dict.get("abstract", "")
        metadata["authors"] = ", ".join(
            [author.get("name", "") for author in response_dict.get("authors", [])]
        )
        metadata["journal"] = response_dict.get("journal", {}).get("name", "")
        metadata["pmid"] = response_dict.get("externalIds", {}).get("PubMed", "")
        metadata["source"] = response_dict.get("source", "")
        metadata["year"] = response_dict.get("year", "")
        metadata["citations"] = [
            {
                "source": "Semantic Scholar",
                "count": response_dict.get("citationCount", ""),
            }
        ]
        return metadata

    def fetch_metadata(self, doi: str) -> dict[str, Any]:
        base_url = f"{self.BASE_URL}/paper/DOI:"
        fields = (
            "paperId,title,abstract,year,venue,journal,fieldsOfStudy,"
            "authors,citationCount,references,citations,isOpenAccess,"
            "openAccessPdf,embedding,tldr,s2FieldsOfStudy,externalIds,url"
        )
        url = f"{base_url}{doi}?fields={fields}"

        response = requests.get(url, timeout=30)

        if response.status_code == 200:
            return response.json()

        return {"error": f"Failed to fetch data, Status Code: {response.status_code}"}

    def get_publication_metadata(self, doi: str) -> dict[str, Any]:
        response = self.fetch_metadata(doi)
        return self.parse_metadata(response, doi)

    def fetch_semanticscholar_citations(self, doi: str) -> dict[str, Any]:
        """
        Keep the old endpoint behavior as closely as possible.
        """
        url = f"{self.BASE_URL}/paper/{doi}/citations"
        params = {"fields": "paperId,title,year"}

        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            return response.json()

        return {
            "error": f"Request failed with status code {response.status_code}",
            "details": response.text,
        }

    def get_metadata_and_citations(self, doi: str) -> dict[str, Any]:
        metadata = self.get_publication_metadata(doi)
        if "error" in metadata:
            return metadata

        citations = self.fetch_semanticscholar_citations(doi)
        metadata["citations"] = citations
        return metadata