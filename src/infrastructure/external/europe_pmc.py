from __future__ import annotations

from typing import Any
import requests


class EuropePmcClient:
    BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/searchPOST"
    REST_BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest"

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
                "count": {"total": result.get("citedByCount", 0)},
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

    def fetch_citations_page(
        self,
        identifier: str,
        source: str,
        page: int = 1,
        page_size: int = 1000,
    ) -> dict[str, Any]:
        """
        Fetch one page of citing publications from Europe PMC.

        Example endpoint:
        /MED/27083558/citations?page=1&pageSize=25&format=json
        """
        url = (
            f"{self.REST_BASE_URL}/{source}/{identifier}/citations"
            f"?page={page}&pageSize={page_size}&format=json"
        )

        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.json()

        return {
            "error": f"Request failed with status code {response.status_code}",
            "details": response.text,
        }

    def fetch_all_citations(
        self,
        identifier: str,
        source: str,
        page_size: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Fetch all citing publications from Europe PMC, following pagination.
        """
        all_citations: list[dict[str, Any]] = []
        page = 1

        while True:
            page_data = self.fetch_citations_page(
                identifier=identifier,
                source=source,
                page=page,
                page_size=page_size,
            )

            if page_data.get("error"):
                break

            citation_list = page_data.get("citationList", {}).get("citation", [])
            if not isinstance(citation_list, list):
                citation_list = []

            all_citations.extend(citation_list)

            hit_count = page_data.get("hitCount", 0)
            if not isinstance(hit_count, int):
                try:
                    hit_count = int(hit_count)
                except Exception:
                    hit_count = 0

            if len(all_citations) >= hit_count or len(citation_list) == 0:
                break

            page += 1

        return all_citations

    def count_citations_per_year(
        self,
        citations: list[dict[str, Any]],
    ) -> dict[str, int]:
        """
        Build a year -> citation count dictionary from Europe PMC citing records.

        Important:
        Each citing publication counts as 1 citation for the target publication.
        We do NOT sum citedByCount from the citing publications.
        """
        counts: dict[str, int] = {}

        for citation in citations:
            if not isinstance(citation, dict):
                continue

            pub_year = citation.get("pubYear")
            if pub_year is None:
                continue

            year = str(pub_year).strip()
            if not year:
                continue

            counts[year] = counts.get(year, 0) + 1

        counts["total"] = len(citations)
        return counts

    def fetch_cited_by_page(
        self,
        identifier: str,
        source: str,
        page: int = 1,
        page_size: int = 1000,
    ) -> dict[str, Any]:
        """
        Fetch one page of publications that cite the given publication.

        Uses the same /{source}/{id}/citations endpoint as fetch_citations_page.
        """
        return self.fetch_citations_page(
            identifier=identifier,
            source=source,
            page=page,
            page_size=page_size,
        )

    def fetch_all_cited_by(
        self,
        identifier: str,
        source: str,
        page_size: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Fetch all publications that cite the given publication.
        """
        return self.fetch_all_citations(
            identifier=identifier,
            source=source,
            page_size=page_size,
        )

    def count_cited_by_per_year(
        self,
        cited_by: list[dict[str, Any]],
    ) -> dict[str, int]:
        """
        Build a year -> count dictionary from Europe PMC cited-by records.
        """
        return self.count_citations_per_year(cited_by)

    def get_metadata_and_citations(self, doi: str) -> dict[str, Any]:
        """
        Fetch publication metadata and all Europe PMC citations grouped per year.
        """
        metadata = self.get_publication_metadata(doi)
        if "error" in metadata:
            return metadata

        pmid = metadata.get("pmid", "")
        source = metadata.get("source", "")

        if pmid and source:
            citations = self.fetch_all_citations(identifier=pmid, source=source)
            citation_counts = self.count_citations_per_year(citations)
            metadata["citations"] = [
                {
                    "source": "Europe PMC",
                    "count": citation_counts,
                }
            ]

        return metadata