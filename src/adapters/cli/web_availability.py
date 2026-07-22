from __future__ import annotations

import argparse
import os
import sys

from pymongo.errors import PyMongoError

from application.use_cases.web_availability.update_web_availability import (
    WebAvailabilityConfig,
    run_update_web_availability,
)
from infrastructure.config import PipelineConfig
from infrastructure.db.repositories import from_config
from infrastructure.external.url_checker import UrlChecker


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Update of web availability + ensure URLs from the tools collection exist."
    )
    # The collections are no longer flags: PipelineConfig reads them from the same
    # env vars these defaulted to (MONGO_TOOLS_COLL, MONGO_WEBAV_COLL) and the
    # repositories below are built pointing at them.
    ap.add_argument("--timeout", type=int, default=int(os.getenv("REQ_TIMEOUT", "15")))
    ap.add_argument("--keep-days", type=int, default=int(os.getenv("KEEP_DAYS", "365")))
    ap.add_argument("--created-by", default=os.getenv("CREATED_BY", "oeb-ingest"))
    ap.add_argument("--updated-by", default=os.getenv("UPDATED_BY", "oeb-ingest"))
    ap.add_argument("--limit-web", type=int, default=0, help="Limit existing web URLs to process (0=all)")
    ap.add_argument("--limit-tools", type=int, default=0, help="Limit tool docs to scan (0=all)")
    ap.add_argument("--dry-run", action="store_true")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    repos = from_config(PipelineConfig.from_env())

    cfg = WebAvailabilityConfig(
        timeout=args.timeout,
        keep_days=args.keep_days,
        created_by=args.created_by,
        updated_by=args.updated_by,
        limit_web=args.limit_web,
        limit_tools=args.limit_tools,
        dry_run=args.dry_run,
    )

    try:
        print("[RUN] web availability job")
        res = run_update_web_availability(cfg, repos, UrlChecker(timeout=cfg.timeout))

        print(
            "[STEP 1] processed existing URLs: "
            f"{res.processed_existing_urls} (step1 errors: {res.step1_errors})"
        )
        print(
            "[STEP 2] tools unique URLs: "
            f"{res.tools_unique_urls} | already present: {res.tools_urls_already_present} | missing: {res.tools_urls_missing}"
        )
        print(
            f"[DONE] inserted missing URLs: {res.inserted_missing_urls} | "
            f"retagged existing URLs: {res.retagged_existing_urls} (insert errors: {res.insert_errors})"
        )
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
