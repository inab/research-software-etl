from __future__ import annotations

from typing import Any

from src.application.services.enrich_publications.helpers import (
    count_citations_per_year,
    remove_empty_fields,
)


class PublicationEnrichmentService:
    """
    Enrich one publication by DOI.

    Main behavior preserved from the original code:
    - metadata comes from Europe PMC
    - citation counts per year come from Semantic Scholar
    """

    def __init__(self, europe_pmc_client, semantic_scholar_client) -> None:
        self.europe_pmc_client = europe_pmc_client
        self.semantic_scholar_client = semantic_scholar_client

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

        # --- Semantic Scholar citations ---
        try:
            citations_response = self.semantic_scholar_client.fetch_semanticscholar_citations(doi)
            processed_citations = count_citations_per_year(citations_response)

            if metadata.get("citations"):
                metadata["citations"].append(
                    {
                        "source": "Semantic Scholar",
                        "count": processed_citations,
                    }
                )
            else:
                metadata["citations"] = [
                    {
                        "source": "Semantic Scholar",
                        "count": processed_citations,
                    }
                ]

            metadata = remove_empty_fields(metadata)
        except Exception as exc:
            print(f"Error fetching metadata from Semantic Scholar for DOI {doi}: {exc}")

        return metadata