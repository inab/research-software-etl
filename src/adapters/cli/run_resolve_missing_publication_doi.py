'''
Test:
python -m adapters.cli.run_resolve_missing_publication_doi \
  --mailto eva.martin@bsc.es \
  --limit 10 \
  --no-update-db \
  --no-write-cache

Real: 
python -m adapters.cli.run_resolve_missing_publication_doi --mailto eva.martin@bsc.es 
'''


from __future__ import annotations

import argparse

from application.use_cases.enrich_publications.resolve_missing_publication_doi import (
    ResolveMissingPublicationDoiUseCase,
)
from application.services.resolve_publication_doi.crossref_doi_resolution_service import (
    CrossrefDoiResolutionService,
)
from infrastructure.config import PipelineConfig
from infrastructure.db.repositories import from_config
from infrastructure.external.crossref import CrossrefClient


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve missing DOIs in publication collection."
    )
    parser.add_argument(
        "--collection-name",
        default="publicationsMetadataDev",
        help="MongoDB collection name",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1000,
        help="Print progress every N processed documents",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of documents to process",
    )
    parser.add_argument(
        "--no-skip-seen",
        action="store_true",
        help="Do not skip documents already present in the cache",
    )
    parser.add_argument(
        "--no-write-cache",
        action="store_true",
        help="Do not write resolved/unresolved results to cache",
    )
    parser.add_argument(
        "--no-update-db",
        action="store_true",
        help="Do not update MongoDB",
    )
    parser.add_argument(
        "--mailto",
        required=True,
        help="Contact email for Crossref polite pool usage",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    repos = from_config(PipelineConfig.from_env())
    publication_repository = repos.publications
    doi_resolution_service = CrossrefDoiResolutionService(
        client=CrossrefClient(mailto=args.mailto)
    )

    use_case = ResolveMissingPublicationDoiUseCase(
        publication_repository=publication_repository,
        doi_resolution_service=doi_resolution_service,
    )

    use_case.execute(
        collection_name=args.collection_name,
        progress_every=args.progress_every,
        limit=args.limit,
        skip_seen=not args.no_skip_seen,
        write_cache=not args.no_write_cache,
        update_db=not args.no_update_db,
    )


if __name__ == "__main__":
    main()