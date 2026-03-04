'''
Usage:

PYTHONPATH=$(pwd) python -m src.adapters.cli.tag_relevant_webavailability_urls
'''

from __future__ import annotations

import argparse
import os
import sys

from pymongo.errors import PyMongoError

from src.application.use_cases.tag_relevant_webavailability_urls import (
    TagRelevantWebAvailabilityConfig,
    run_tag_relevant_webavailability_urls,
)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Tag relevant URLs in webAvailabilityDev based on toolsDev types and webpages."
    )
    ap.add_argument("--tools-coll", default=os.getenv("MONGO_TOOLS_COLL", "toolsDev"))
    ap.add_argument("--web-coll", default=os.getenv("MONGO_WEBAV_COLL", "webAvailabilityDev"))
    ap.add_argument("--created-by", default=os.getenv("CREATED_BY", "oeb-ingest"))
    ap.add_argument("--updated-by", default=os.getenv("UPDATED_BY", "oeb-ingest"))
    ap.add_argument("--tag-field", default=os.getenv("WEBAV_RELEVANT_TAG_FIELD", "is_relevant"))
    ap.add_argument("--limit-tools", type=int, default=0, help="Limit tool docs to scan (0=all)")
    ap.add_argument("--dry-run", action="store_true")
    return ap


def main() -> int:
    args = build_parser().parse_args()

    cfg = TagRelevantWebAvailabilityConfig(
        tools_collection=args.tools_coll,
        web_collection=args.web_coll,
        created_by=args.created_by,
        updated_by=args.updated_by,
        tag_field=args.tag_field,
        limit_tools=args.limit_tools,
        dry_run=args.dry_run,
    )

    try:
        print("[RUN] Tag relevant webAvailability URLs")
        res = run_tag_relevant_webavailability_urls(cfg)

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