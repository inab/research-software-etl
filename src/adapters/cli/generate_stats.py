"""
Command-line interface for generating statistics.
"""

import argparse
import logging
from dotenv import load_dotenv
from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from src.application.use_cases.stats.generate_stats import generate_stats_for_collections


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
        help="Set the logging level",
        default="INFO",
    )

    args = parser.parse_args()
    load_dotenv(args.env_file)
    numeric_level = getattr(logging, args.loglevel.upper())
    logging.basicConfig(level=numeric_level)
    logging.debug(f"Env file: {args.env_file}")

    if args.collections.lower() == "all":
        collections = ['RIS3CAT VEIS', 'ELIXIR-ES', 'BioExcel', 'PerMedCoE', 'IMPaCT-Data', '3D-BioInfo', 'EUCAIM', 'Proteomics']
        if "tools" not in collections:
            collections.append("tools")
    else:
        collections = [c.strip() for c in args.collections.split(",") if c.strip()]

    logging.info(f"Generating stats for collections: {collections}")
    generate_stats_for_collections(collections)
    logging.info("Stats generation complete.")

if __name__ == "__main__":
    main()

