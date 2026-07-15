"""
Application use case: enrich the publications collection from DOI metadata.

This module defines the collection-level enrichment workflow for publication
records. Given a publications collection, the use case scans records with a
DOI, normalizes and validates each DOI, skips already seen identifiers when
configured, optionally skips records that already contain Europe PMC citation
information, retrieves enriched metadata and citation counts from Europe PMC,
and updates the corresponding database records.
"""

from __future__ import annotations

from datetime import datetime

from application.services.enrich_publications.doi_service import normalize_doi


class EnrichPublicationCollectionUseCase:
    def __init__(
        self,
        publication_repository,
        enrichment_cache,
        enrichment_service,
    ) -> None:
        self.publication_repository = publication_repository
        self.enrichment_cache = enrichment_cache
        self.enrichment_service = enrichment_service

    @staticmethod
    def _has_europe_pmc_yearly_citations(doc: dict) -> bool:
        """
        Return True only if the publication already has a Europe PMC citation
        entry with a *per-year* breakdown.

        A ``count`` of just ``{"total": N}`` (no year keys) means the yearly
        breakdown was never obtained -- such records still need enrichment, so
        they must not be treated as done.
        """
        data = doc.get("data", {})
        entries = data.get("citations", [])
        if not isinstance(entries, list):
            return False
        for e in entries:
            if isinstance(e, dict) and e.get("source") == "Europe PMC":
                count = e.get("count")
                if isinstance(count, dict) and any(k != "total" for k in count):
                    return True
        return False

    def execute(
        self,
        collection_name: str = "publicationsMetadataDev",
        progress_every: int = 1000,
        limit: int | None = None,
        skip_seen: bool = True,
        skip_if_has_europe_pmc_citations: bool = True,
        write_cache: bool = True,
        update_db: bool = True,
        target_dois: set[str] | None = None,
    ) -> None:
        seen_dois = self.enrichment_cache.load_seen_dois() if skip_seen else set()
        print(f"Already seen {len(seen_dois)} DOIs")

        processed = 0
        updated = 0
        skipped_seen = 0
        skipped_invalid = 0
        skipped_existing_epmc_citations = 0
        no_metadata = 0

        for doc in self.publication_repository.fetch_with_doi(collection_name):
            if limit is not None and processed >= limit:
                break

            processed += 1

            if (
                skip_if_has_europe_pmc_citations
                and self._has_europe_pmc_yearly_citations(doc)
            ):
                skipped_existing_epmc_citations += 1
                continue

            doc_id = doc.get("_id")
            raw_doi = doc.get("data", {}).get("doi")
            doi = normalize_doi(raw_doi)

            if not doi:
                print(f"Skipping invalid DOI: {raw_doi}")
                skipped_invalid += 1
                continue

            doi_lower = doi.lower()

            if target_dois is not None and doi_lower not in target_dois:
                continue

            if skip_seen and doi_lower in seen_dois:
                skipped_seen += 1
                continue

            metadata = self.enrichment_service.enrich_by_doi(doi)

            if not metadata or metadata.get("error"):
                print(f"No metadata found for DOI {doi}")
                no_metadata += 1
                continue

            if update_db:
                self.publication_repository.update_publication_data(
                    collection_name=collection_name,
                    document_id=doc_id,
                    data=metadata,
                    last_updated_at=datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                )

            if write_cache:
                self.enrichment_cache.append(metadata)

            seen_dois.add(doi_lower)
            updated += 1

            if progress_every > 0 and processed % progress_every == 0:
                print(
                    f"Processed {processed} docs | "
                    f"updated={updated} | "
                    f"skipped_seen={skipped_seen} | "
                    f"skipped_invalid={skipped_invalid} | "
                    f"skipped_existing_epmc_citations={skipped_existing_epmc_citations} | "
                    f"no_metadata={no_metadata}"
                )

        print(
            f"Done. Processed={processed}, updated={updated}, "
            f"skipped_seen={skipped_seen}, "
            f"skipped_invalid={skipped_invalid}, "
            f"skipped_existing_epmc_citations={skipped_existing_epmc_citations}, "
            f"no_metadata={no_metadata}"
        )
