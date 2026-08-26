"""
Command-line interface for generating statistics.
"""

import argparse
import logging
import os
from dotenv import load_dotenv
from application.use_cases.stats.generate_stats import generate_stats_for_collections
from infrastructure.config import PipelineConfig
from infrastructure.db.repositories import from_config
from infrastructure.logging_config import resolve_level


def main():
    parser = argparse.ArgumentParser(
        description="Generate statistics for research software collections."
    )
    parser.add_argument(
        "--collections", "-c",
        help="Comma-separated list of collection tags, or 'all' for all collections.",
        required=True,
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
    load_dotenv(args.env_file)
    logging.basicConfig(level=resolve_level(args.loglevel))
    logging.debug(f"Env file: {args.env_file}")

    if args.collections.lower() == "all":
        collections = ['RIS3CAT VEIS', 'ELIXIR-ES', 'BioExcel', 'PerMedCoE', 'IMPaCT-Data', '3D-BioInfo', 'EUCAIM', 'Proteomics']
        if "tools" not in collections:
            collections.append("tools")
    else:
        collections = [c.strip() for c in args.collections.split(",") if c.strip()]

    repos = from_config(PipelineConfig.from_env())

    logging.info(f"Generating stats for collections: {collections}")
    generate_stats_for_collections(collections, repos)
    
    logging.info("Stats generation complete.")

if __name__ == "__main__":
    main()

