"""
Reindex stage: rebuild the API's tools indexes after a run is promoted.

Merge promotes a freshly-built tools collection that carries nothing but its
default `_id` index, so the API's `/search` text index and filter indexes are
gone until they are recreated. This stage asks the API to do that (the index
definitions live in the API repo; the pipeline only triggers them).

Runs after `merge`. By the time it runs the collection is already live, so an
API failure must not fail the run: it warns loudly with the manual remediation
and exits 0. A missing token, by contrast, is a misconfiguration and exits
non-zero -- the orchestrator also checks it up front, before merge promotes.
"""

import argparse
import logging
from dotenv import load_dotenv

logger = logging.getLogger("rs-etl-pipeline")


def main():
    parser = argparse.ArgumentParser(
        description="Rebuild the API's tools indexes after promotion."
    )
    parser.add_argument(
        "--force-text",
        help=(
            "Drop and rebuild the full-text index (needed only when its fields or "
            "weights changed). Off by default; a plain reindex leaves it in place."
        ),
        action="store_true",
        dest="force_text",
    )
    parser.add_argument(
        "--env-file",
        "-e",
        help="File containing environment variables to be set before running.",
        default=".env",
    )
    args = parser.parse_args()

    load_dotenv(args.env_file)

    from infrastructure.config import Credentials, PipelineConfig
    from infrastructure.external.observatory_api import ObservatoryApiClient

    config = PipelineConfig.from_env()
    creds = Credentials.from_env().require("observatory_admin_token")

    client = ObservatoryApiClient(
        config.observatory_api_url, creds.observatory_admin_token
    )
    try:
        result = client.ensure_tools_indexes(force_text=args.force_text)
        print(f"Rebuilt tools indexes via {config.observatory_api_url}")
        logger.info("Reindex response: %s", result)
    except Exception as exc:
        # The collection is already live; do not fail the run. The next API
        # restart also re-ensures indexes, so this closes the window rather than
        # being the only path.
        logger.error(
            "Reindex call failed: %s. The live tools collection has only its _id "
            "index -- /search will fail until indexes are rebuilt. Restart the API "
            "or run its scripts/create_indexes.py.",
            exc,
        )
        print(
            "⚠️  Reindex failed -- tools are promoted but /search indexes are "
            "missing. Restart the API or run scripts/create_indexes.py."
        )


if __name__ == "__main__":
    main()
