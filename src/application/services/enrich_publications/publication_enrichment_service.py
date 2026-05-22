from __future__ import annotations

from typing import Any

from application.services.enrich_publications.helpers import remove_empty_fields


class PublicationEnrichmentService:
    """
    Enrich one publication by DOI using Europe PMC only.

    Behavior:
    - metadata and total citation count come from Europe PMC
    - citedBy (full article list) is not stored; the frontend queries Europe PMC directly
    """

    def __init__(self, europe_pmc_client) -> None:
        self.europe_pmc_client = europe_pmc_client

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

        # --- Europe PMC per-year citation counts ---
        # citedBy (full article list) is not stored; the frontend queries Europe PMC directly
        try:
            pmid = metadata.get("pmid", "")
            source = metadata.get("source", "")

            if pmid and source:
                citing_publications = self.europe_pmc_client.fetch_all_citations(
                    identifier=pmid,
                    source=source,
                )
                counts_per_year = self.europe_pmc_client.count_citations_per_year(
                    citing_publications
                )
                metadata["citations"] = [{"source": "Europe PMC", "count": counts_per_year}]

            metadata = remove_empty_fields(metadata)

        except Exception as exc:
            print(f"Error fetching citations from Europe PMC for DOI {doi}: {exc}")

        return metadata