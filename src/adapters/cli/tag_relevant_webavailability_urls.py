'''
Usage:

PYTHONPATH=$(pwd) python -m adapters.cli.tag_relevant_webavailability_urls
'''

from __future__ import annotations

import argparse
import os
import sys

from pymongo.errors import PyMongoError

from application.use_cases.web_availability.tag_relevant_webavailability_urls import (
    TagRelevantWebAvailabilityConfig,
    run_tag_relevant_webavailability_urls,
)
from infrastructure.config import PipelineConfig
from infrastructure.db.repositories import Repositories


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Tag relevant URLs in the web-availability collection based on tool types and webpages."
    )
    # The collections and the tag field are no longer flags: PipelineConfig reads the
    # collection names from the same env vars these defaulted to (MONGO_TOOLS_COLL,
    # MONGO_WEBAV_COLL), and the tag field belongs to the repository's schema.
    ap.add_argument("--created-by", default=os.getenv("CREATED_BY", "oeb-ingest"))
    ap.add_argument("--updated-by", default=os.getenv("UPDATED_BY", "oeb-ingest"))
    ap.add_argument("--limit-tools", type=int, default=0, help="Limit tool docs to scan (0=all)")
    ap.add_argument("--dry-run", action="store_true")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    repos = Repositories.from_config(PipelineConfig.from_env())

    cfg = TagRelevantWebAvailabilityConfig(
        created_by=args.created_by,
        updated_by=args.updated_by,
        limit_tools=args.limit_tools,
        dry_run=args.dry_run,
    )

    try:
        print("[RUN] Tag relevant webAvailability URLs")
        res = run_tag_relevant_webavailability_urls(cfg, repos)

        print(f"[INFO] tools scanned: {res.tools_scanned}")
        print(f"[INFO] tools matched relevant types: {res.tools_matched}")
        print(f"[INFO] relevant URLs found: {res.relevant_urls_found}")
        print(f"[DONE] upserts sent: {res.upserts_sent}")
        if cfg.dry_run:
            print("[DRY-RUN] No DB changes were written.")
        return 0

    except PyMongoError as e:
        print(f"[FATAL] Mongo error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"[FATAL] Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
