'''
python -m src.adapters.cli.enrich_publications_cli
python -m src.adapters.cli.enrich_publications_cli --limit 100
python -m src.adapters.cli.enrich_publications_cli --progress-every 100
python -m src.adapters.cli.enrich_publications_cli --no-update-db
'''

from __future__ import annotations

import argparse
import sys

from src.application.services.enrich_publications.publication_enrichment_service import (
    PublicationEnrichmentService,
)
from src.application.use_cases.enrich_publications.enrich_publications_collection import (
    EnrichPublicationCollectionUseCase,
)
from src.infrastructure.db.mongo.publications_repository import (
    MongoPublicationRepository,
)
from src.infrastructure.external.europe_pmc import EuropePmcClient
from src.infrastructure.external.semantic_scholar import SemanticScholarClient
from src.infrastructure.storage.jsonl import JsonlPublicationEnrichmentCache


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Enrich publication metadata using Europe PMC and Semantic Scholar."
    )
    parser.add_argument(
        "--collection",
        default="publicationsMetadataDev",
        help="MongoDB collection name.",
    )
    parser.add_argument(
        "--jsonl-path",
        default="scripts/data/publications_enrichment.jsonl",
        help="Path to JSONL cache/output file.",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1000,
        help="Print progress every N processed documents.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of documents to process.",
    )
    parser.add_argument(
        "--no-skip-seen",
        action="store_true",
        help="Do not skip DOIs already present in the JSONL file.",
    )
    parser.add_argument(
        "--no-write-cache",
        action="store_true",
        help="Do not append results to the JSONL file.",
    )
    parser.add_argument(
        "--no-update-db",
        action="store_true",
        help="Do not update MongoDB.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show configuration and exit without running.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    publication_repository = MongoPublicationRepository()
    enrichment_cache = JsonlPublicationEnrichmentCache(args.jsonl_path)
    enrichment_service = PublicationEnrichmentService(
        europe_pmc_client=EuropePmcClient(),
        semantic_scholar_client=SemanticScholarClient(),
    )

    use_case = EnrichPublicationCollectionUseCase(
        publication_repository=publication_repository,
        enrichment_cache=enrichment_cache,
        enrichment_service=enrichment_service,
    )

    config = {
        "collection_name": args.collection,
        "progress_every": args.progress_every,
        "limit": args.limit,
        "skip_seen": not args.no_skip_seen,
        "write_cache": not args.no_write_cache,
        "update_db": not args.no_update_db,
    }

    if args.dry_run:
        print("Dry run. Configuration:")
        for key, value in config.items():
            print(f"  {key}: {value}")
        return 0

    try:
        use_case.execute(**config)
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130
    except Exception as exc:
        print(f"Execution failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())