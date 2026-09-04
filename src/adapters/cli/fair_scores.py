"""
Command-line interface for generating FAIR indicators and scores for tools.
"""

import argparse
import logging
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

from application.use_cases.stats.generate_fair_scores import add_fair_scores
from infrastructure.config import PipelineConfig
from infrastructure.db.repositories import from_config
from infrastructure.logging_config import resolve_level



def main():
    parser = argparse.ArgumentParser(
        description="Generate FAIR indicators and scores for research software tools."
    )
    parser.add_argument(
        "--collections", "-c",
        help=(
            "Tool selection scope. "
            "Use 'tools' to process all tools, or provide a tag to process only tools "
            "whose data.tags contains that value."
        ),
        required=True,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of tools to process.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recomputation even when stored scores are already up to date.",
    )
    parser.add_argument(
        "--updated-within-days",
        type=int,
        default=30,
        dest="updated_within_days",
        help=(
            "Only score tools whose merge timestamp is within the last N days "
            "(default: 30). A tool's timestamp is bumped by merge only when its "
            "content changed, so this scopes scoring to recently changed tools. "
            "Use 0 (or a negative value) to score every tool."
        ),
    )
    parser.add_argument(
        "--env-file", "-e",
        help="File containing environment variables to be set before running.",
        default=".env",
    )
    parser.add_argument(
        "--loglevel", "-l",
        help="Set the logging level (default: LOG_LEVEL env var, else INFO).",
        default=os.getenv("LOG_LEVEL", "INFO"),
    )

    args = parser.parse_args()

    load_dotenv(args.env_file, override=True)

    logging.basicConfig(level=resolve_level(args.loglevel))
    logging.debug(f"Env file: {args.env_file}")

    if args.collections.lower() == "all":
        collections = ['tools']

    else:
        collections = [c.strip() for c in args.collections.split(",") if c.strip()]

    repos = from_config(PipelineConfig.from_env())

    # Compute the incremental cutoff here, at the CLI layer, so nothing below
    # adapters/ has to deal with clocks. A non-positive window means "no date
    # filter" -> score every tool. Mirrors the transformation stage's
    # --updated-within-days.
    if args.updated_within_days > 0:
        updated_since = (datetime.now() - timedelta(days=args.updated_within_days)).isoformat()
        logging.info(
            f"Scoring tools updated since {updated_since} "
            f"(last {args.updated_within_days} days)"
        )
    else:
        updated_since = None
        logging.info("Scoring every tool (no date filter)")

    for collection in collections:
        logging.info(
            f"Generating FAIR indicators/scores for selection: {collection}"
        )
        add_fair_scores(
            repos,
            tag_or_tools=collection,
            limit=args.limit,
            force=args.force,
            updated_since=updated_since,
        )
        logging.info(
            f"Generation of FAIR indicators/scores complete for {collection}"
        )

    logging.info("FAIR indicators/scores generation complete.")



if __name__ == "__main__":
    main()