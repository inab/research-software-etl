from __future__ import annotations

from datetime import datetime

from application.services.resolve_publication_doi.cache_utils import (
    append_jsonl_record,
    load_seen_document_ids,
)
from infrastructure.config import PipelineConfig


class ResolveMissingPublicationDoiUseCase:
    def __init__(
        self,
        publication_repository,
        doi_resolution_service,
        config: PipelineConfig = None,
    ) -> None:
        self.publication_repository = publication_repository
        self.doi_resolution_service = doi_resolution_service
        self.config = config or PipelineConfig()

    def execute(
        self,
        collection_name: str = None,
        progress_every: int = 1000,
        limit: int | None = None,
        skip_seen: bool = True,
        write_cache: bool = True,
        update_db: bool = True,
        resolved_cache_path: str = None,
        unresolved_cache_path: str = None,
    ) -> None:
        collection_name = collection_name or self.config.publications_collection
        resolved_cache_path = resolved_cache_path or self.config.resolved_dois_path
        unresolved_cache_path = unresolved_cache_path or self.config.unresolved_dois_path

        seen_doc_ids = (
            load_seen_document_ids(
                resolved_path=resolved_cache_path,
                unresolved_path=unresolved_cache_path,
            )
            if skip_seen
            else set()
        )
        print(f"Already seen {len(seen_doc_ids)} documents")

        processed = 0
        resolved = 0
        skipped_seen = 0
        skipped_missing_title = 0
        unresolved = 0

        for doc in self.publication_repository.fetch_without_doi(collection_name):
            if limit is not None and processed >= limit:
                break

            processed += 1

            doc_id = doc.get("_id")
            doc_id_str = str(doc_id)

            if skip_seen and doc_id_str in seen_doc_ids:
                skipped_seen += 1
                continue

            data = doc.get("data", {})
            title = data.get("title")
            journal = data.get("journal")
            year = data.get("year")

            if not title or not str(title).strip():
                print(f"Skipping document without usable title: {doc_id}")
                skipped_missing_title += 1
                continue

            resolution = self.doi_resolution_service.resolve(
                title=title,
                journal=journal,
                year=year,
            )

            if not resolution:
                print(f"No DOI found for document {doc_id}")
                unresolved += 1

                if write_cache:
                    append_jsonl_record(
                        unresolved_cache_path,
                        {
                            "document_id": doc_id_str,
                            "title": title,
                            "journal": journal,
                            "year": year,
                            "checked_at": datetime.utcnow().isoformat(),
                        },
                    )

                seen_doc_ids.add(doc_id_str)
                continue

            doi = resolution["doi"]

            if update_db:
                self.publication_repository.update_publication_doi(
                    collection_name=collection_name,
                    document_id=doc_id,
                    doi=doi,
                    doi_resolution_source=resolution.get("source"),
                    doi_resolution_confidence=resolution.get("confidence"),
                    doi_resolution_match_title=resolution.get("matched_title"),
                    doi_resolution_match_journal=resolution.get("matched_journal"),
                    doi_resolution_match_year=resolution.get("matched_year"),
                    last_updated_at=datetime.utcnow().isoformat(),
                )

            if write_cache:
                append_jsonl_record(
                    resolved_cache_path,
                    {
                        "document_id": doc_id_str,
                        "title": title,
                        "journal": journal,
                        "year": year,
                        **resolution,
                        "resolved_at": datetime.utcnow().isoformat(),
                    },
                )

            seen_doc_ids.add(doc_id_str)
            resolved += 1

            if progress_every > 0 and processed % progress_every == 0:
                print(
                    f"Processed {processed} docs | "
                    f"resolved={resolved} | skipped_seen={skipped_seen} | "
                    f"skipped_missing_title={skipped_missing_title} | "
                    f"unresolved={unresolved}"
                )

        print(
            f"Done. Processed={processed}, resolved={resolved}, "
            f"skipped_seen={skipped_seen}, skipped_missing_title={skipped_missing_title}, "
            f"unresolved={unresolved}"
        )