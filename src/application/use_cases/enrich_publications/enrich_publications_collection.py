from __future__ import annotations

from datetime import datetime

from src.application.services.enrich_publications.doi_service import normalize_doi


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

    def execute(
        self,
        collection_name: str = "publicationsMetadataDev",
        progress_every: int = 1000,
        limit: int | None = None,
        skip_seen: bool = True,
        write_cache: bool = True,
        update_db: bool = True,
    ) -> None:
        seen_dois = self.enrichment_cache.load_seen_dois() if skip_seen else set()
        print(f"Already seen {len(seen_dois)} DOIs")

        processed = 0
        updated = 0
        skipped_seen = 0
        skipped_invalid = 0

        for doc in self.publication_repository.fetch_with_doi(collection_name):
            if limit is not None and processed >= limit:
                break

            processed += 1

            doc_id = doc.get("_id")
            raw_doi = doc.get("data", {}).get("doi")
            doi = normalize_doi(raw_doi)

            if not doi:
                print(f"Skipping invalid DOI: {raw_doi}")
                skipped_invalid += 1
                continue

            doi_lower = doi.lower()
            if skip_seen and doi_lower in seen_dois:
                skipped_seen += 1
                continue

            metadata = self.enrichment_service.enrich_by_doi(doi)

            if not metadata:
                print(f"No metadata found for DOI {doi}")
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
                    f"updated={updated} | skipped_seen={skipped_seen} | "
                    f"skipped_invalid={skipped_invalid}"
                )

        print(
            f"Done. Processed={processed}, updated={updated}, "
            f"skipped_seen={skipped_seen}, skipped_invalid={skipped_invalid}"
        )