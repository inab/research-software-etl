"""
Command-line interface for generating FAIR indicators and scores for tools.
"""

import argparse
import logging

from dotenv import load_dotenv

from application.use_cases.stats.generate_fair_scores import add_fair_scores


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
        "--env-file", "-e",
        help="File containing environment variables to be set before running.",
        default=".env",
    )
    parser.add_argument(
        "--loglevel", "-l",
        help="Set the logging level.",
        default="INFO",
    )

    args = parser.parse_args()

    load_dotenv(args.env_file, override=True)

    numeric_level = getattr(logging, args.loglevel.upper(), logging.INFO)
    logging.basicConfig(level=numeric_level)
    logging.debug(f"Env file: {args.env_file}")

    if args.collections.lower() == "all":
        collections = ['RIS3CAT VEIS', 'ELIXIR-ES', 'BioExcel', 'PerMedCoE', 'IMPaCT-Data', '3D-BioInfo', 'EUCAIM', 'Proteomics']
        if "tools" not in collections:
            collections.append("tools")
    else:
        collections = [c.strip() for c in args.collections.split(",") if c.strip()]



    for collection in collections:
        logging.info(
            f"Generating FAIR indicators/scores for selection: {collection}"
            )
        add_fair_scores(
            tag_or_tools=collection,
            limit=args.limit,
        )

    logging.info("FAIR indicators/scores generation complete.")


if __name__ == "__main__":
    main()