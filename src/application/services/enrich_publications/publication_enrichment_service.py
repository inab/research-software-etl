from __future__ import annotations

from typing import Any

from application.services.enrich_publications.helpers import remove_empty_fields


class PublicationEnrichmentService:
    """
    Enrich one publication by DOI using Europe PMC only.

    Behavior:
    - metadata comes from Europe PMC
    - citations are fetched from Europe PMC and grouped by publication year
    """

    def __init__(self, europe_pmc_client) -> None:
        self.europe_pmc_client = europe_pmc_client
        self.europe_pmc_citation_error_count = 0

    def enrich_by_doi(self, doi: str) -> dict[str, Any]:
        metadata: dict[str, Any] = {}

        # --- Europe PMC metadata ---
        try:
            metadata = self.europe_pmc_client.get_publication_metadata(doi) or {}
            metadata = remove_empty_fields(metadata)
        except Exception as exc:
            print(f"Error fetching metadata from Europe PMC for DOI {doi}: {exc}")
            metadata = {}

        # Ensure DOI is present even if Europe PMC fails
        metadata["doi"] = doi

        if "error" in metadata:
            return metadata

        # --- Europe PMC citations per year ---
        try:
            pmid = metadata.get("pmid", "")
            source = metadata.get("source", "")

            if pmid and source:
                citations = self.europe_pmc_client.fetch_all_citations(
                    identifier=pmid,
                    source=source,
                )
                processed_citations = self.europe_pmc_client.count_citations_per_year(
                    citations
                )

                metadata["citations"] = [
                    {
                        "source": "Europe PMC",
                        "count": processed_citations,
                    }
                ]

            metadata = remove_empty_fields(metadata)

        except Exception as exc:
            self.europe_pmc_citation_error_count += 1
            print(f"Error fetching citations from Europe PMC for DOI {doi}: {exc}")

        return metadata