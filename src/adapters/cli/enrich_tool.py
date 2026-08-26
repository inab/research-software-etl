"""
Command-line interface for (re)generating all derived data for one tool.

``rsetl enrich-tool <tool_id>`` refreshes a single tool's FAIR score, web
availability and similarity neighbours, using the cached embedding corpus so it
does not have to re-embed every tool. Run the full similarity stage at least once
first to populate that cache.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

from application.services.stats_generation.similarity.compute_embeddings import (
    load_embedder,
)
from application.use_cases.records.generate_record_data import generate_record_data
from application.use_cases.web_availability.update_web_availability import (
    WebAvailabilityConfig,
)
from infrastructure.config import Credentials, PipelineConfig
from infrastructure.db.repositories import from_config
from infrastructure.external.url_checker import UrlChecker
from infrastructure.logging_config import resolve_level


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="rsetl enrich-tool",
        description=(
            "Regenerate FAIR scores, web availability and similar tools for a "
            "single tool, identified by its _id."
        ),
    )
    ap.add_argument("tool_id", help="The _id of the tool to enrich.")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Recompute the FAIR score even when the stored one is up to date.",
    )

    sim = ap.add_argument_group("similarity")
    sim.add_argument(
        "--k", type=int, default=12, help="Neighbours to store (default: 12)."
    )
    sim.add_argument(
        "--model",
        default="Alibaba-NLP/gte-modernbert-base",
        help="Embedding model. Must match the model the cache was built with.",
    )
    sim.add_argument("--batch-size", type=int, default=64, help="Encoding batch size.")
    sim.add_argument(
        "--no-reverse-update",
        dest="reverse_update",
        action="store_false",
        help="Do not insert this tool into other tools' neighbour lists.",
    )
    sim.add_argument(
        "--reverse-candidates",
        type=int,
        default=None,
        help="How many of the tool's top neighbours to reverse-update (default: k).",
    )

    web = ap.add_argument_group("web availability")
    web.add_argument("--timeout", type=int, default=int(os.getenv("REQ_TIMEOUT", "15")))
    web.add_argument(
        "--keep-days", type=int, default=int(os.getenv("KEEP_DAYS", "365"))
    )
    web.add_argument("--created-by", default=os.getenv("CREATED_BY", "oeb-ingest"))
    web.add_argument("--updated-by", default=os.getenv("UPDATED_BY", "oeb-ingest"))
    web.add_argument(
        "--dry-run",
        action="store_true",
        help="Probe URLs but write nothing to the web-availability collection.",
    )

    ap.add_argument("--env-file", "-e", default=".env", help="Env file to load.")
    ap.add_argument(
        "--loglevel",
        "-l",
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Logging level (default: LOG_LEVEL env var, else INFO).",
    )
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    load_dotenv(args.env_file, override=True)
    logging.basicConfig(level=resolve_level(args.loglevel))

    config = PipelineConfig.from_env()
    repos = from_config(config)
    creds = Credentials.from_env()

    url_checker = UrlChecker(timeout=args.timeout)
    wa_config = WebAvailabilityConfig(
        timeout=args.timeout,
        keep_days=args.keep_days,
        created_by=args.created_by,
        updated_by=args.updated_by,
        dry_run=args.dry_run,
    )

    def make_embedder():
        return load_embedder(
            args.model,
            hf_token=creds.huggingface_api_key,
            batch_size=args.batch_size,
        )

    try:
        result = generate_record_data(
            repos,
            tool_id=args.tool_id,
            url_checker=url_checker,
            make_embedder=make_embedder,
            model_name=args.model,
            k=args.k,
            force=args.force,
            reverse_update=args.reverse_update,
            reverse_candidates=args.reverse_candidates,
            wa_config=wa_config,
        )
    except ValueError as exc:
        # The one hard error: the tool id matched nothing.
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    fair = result["fair"]
    web = result["web_availability"]
    sim = result["similarity"]

    print(f"[DONE] enrich-tool {result['tool_id']} ({result['tool_name']})")

    print(f"  FAIR:         {fair.get('error') or fair['status']}")

    if web.get("error"):
        print(f"  web:          FAILED — {web['error']}")
    else:
        print(
            "  web:          "
            f"relevant={web['relevant']} probed={web['probed']} urls={web['urls']}"
        )

    if sim.get("error"):
        # The common case is an unpopulated cache; point at the fix.
        print(f"  similarity:   FAILED — {sim['error']}")
    else:
        print(
            "  similarity:   "
            f"neighbours={sim['neighbours']} reverse_updated={sim['reverse_updated']}"
        )

    if args.dry_run:
        print("  [DRY-RUN] No web-availability changes were written.")

    if not result["ok"]:
        print(
            f"[WARN] Some stages failed: {', '.join(result['failed_stages'])}.",
            file=sys.stderr,
        )
        if "similarity" in result["failed_stages"]:
            print(
                "[HINT] similarity needs the embedding cache. Populate it once with "
                "the full similarity stage (run it with --force), then re-run.",
                file=sys.stderr,
            )
        return 3

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
