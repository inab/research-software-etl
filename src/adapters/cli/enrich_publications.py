"""
python -m adapters.cli.enrich_publications
python -m adapters.cli.enrich_publications --limit 100
python -m adapters.cli.enrich_publications --progress-every 100
python -m adapters.cli.enrich_publications --no-update-db
python -m adapters.cli.enrich_publications --no-skip-existing-europe-pmc-citations
"""

from __future__ import annotations

import argparse
import sys

from application.services.enrich_publications.doi_service import normalize_doi
from application.services.enrich_publications.publication_enrichment_service import (
    PublicationEnrichmentService,
)
from application.use_cases.enrich_publications.enrich_publications_collection import (
    EnrichPublicationCollectionUseCase,
)
from infrastructure.config import PipelineConfig
from infrastructure.db.repositories import Repositories
from infrastructure.external.europe_pmc import EuropePmcClient
from infrastructure.storage.jsonl import JsonlPublicationEnrichmentCache


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Enrich publication metadata and citation counts using Europe PMC, "
            "skipping records that already contain Europe PMC citations."
        )
    )
    parser.add_argument(
        "--collection",
        default="publicationsMetadataDev",
        help="MongoDB collection name.",
    )
    parser.add_argument(
        "--jsonl-path",
        default="data/cache/publications_enrichment.jsonl",
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
        "--reset-cache",
        action="store_true",
        help="Delete the existing JSONL cache before starting, then enrich from scratch.",
    )
    parser.add_argument(
        "--no-skip-existing-europe-pmc-citations",
        action="store_true",
        help="Process records even if they already contain Europe PMC citations.",
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
        "--dois-file",
        default=None,
        help="Path to a text file with one DOI per line. Only those documents are processed.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show configuration and exit without running.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    repos = Repositories.from_config(PipelineConfig.from_env())
    publication_repository = repos.publications
    enrichment_cache = JsonlPublicationEnrichmentCache(args.jsonl_path)
    enrichment_service = PublicationEnrichmentService(
        europe_pmc_client=EuropePmcClient(),
    )

    use_case = EnrichPublicationCollectionUseCase(
        publication_repository=publication_repository,
        enrichment_cache=enrichment_cache,
        enrichment_service=enrichment_service,
    )

    target_dois: set[str] | None = None
    if args.dois_file:
        import pathlib
        lines = pathlib.Path(args.dois_file).read_text().splitlines()
        target_dois = {
            normalize_doi(line.strip()).lower()
            for line in lines
            if line.strip() and normalize_doi(line.strip())
        }
        print(f"Targeting {len(target_dois)} DOIs from {args.dois_file}")

    config = {
        "collection_name": args.collection,
        "progress_every": args.progress_every,
        "limit": args.limit,
        "skip_seen": not args.no_skip_seen,
        "skip_if_has_europe_pmc_citations": (
            not args.no_skip_existing_europe_pmc_citations
        ),
        "write_cache": not args.no_write_cache,
        "update_db": not args.no_update_db,
        "target_dois": target_dois,
    }

    if args.dry_run:
        print("Dry run. Configuration:")
        for key, value in config.items():
            print(f"  {key}: {value}")
        return 0

    if args.reset_cache:
        enrichment_cache.clear()
        print(f"Cache cleared: {args.jsonl_path}")

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