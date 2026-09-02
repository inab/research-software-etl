"""
The command-line interface for the transformer
possible sources : [
    'bioconda', 
    'bioconda_recipes', 
    'github', 
    'biotools', 
    'bioconductor', 
    'galaxy_metadata', 
    'toolshed', 
    'galaxy', 
    'sourceforge', 
    'opeb_metrics'
    ]

Example of usage:
python src/adapters/cli/transformation/transformation.py -e .env -s bioconda_recipes github
python src/adapters/cli/transformation/transformation.py -e .env -s all
"""
import argparse
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from infrastructure.logging_config import resolve_level, setup_logging

# Verbosity is controlled by the LOG_LEVEL env var (default INFO), e.g.
# LOG_LEVEL=DEBUG or LOG_LEVEL=WARNING. It propagates to every `rsetl run` stage
# because each stage runs as its own subprocess.
logger = setup_logging(resolve_level(os.getenv("LOG_LEVEL")))

ALL_SOURCES = [
            "bioconda", 
            "bioconda_recipes", 
            "github", 
            "biotools", 
            "bioconductor", 
            "galaxy_metadata", 
            "toolshed", 
            "galaxy", 
            "sourceforge", 
            "opeb_metrics"
        ]


def main():
    parser = argparse.ArgumentParser(
        description="Transform raw data from different sources into a common format."
    )
    parser.add_argument(
        "--env-file", "-e",
        help=("File containing environment variables to be set before running "),
        default=".env",
    )

    parser.add_argument(
        "--sources", "-s",
        help=("Sources to transform. The posiblities are: bioconda, bioconda_recipes, github, biotools, bioconductor, galaxy_metadata, toolshed, galaxy, sourceforge and opeb_metrics, or all to include all of them. Default is all sources."),
        nargs='+',
        default=['all'],
        dest="sources"
    )

    parser.add_argument(
        "--updated-within-days",
        type=int,
        default=30,
        dest="updated_within_days",
        help=("Only transform raw entries whose @last_updated_at is within the last "
              "N days (default: 30). Use 0 (or a negative value) for a full "
              "re-transform of every entry."),
    )

    args = parser.parse_args()

    # Load the environment variables ------------------------------------------
    logger.debug(f"Env file: {args.env_file}")
    load_dotenv(args.env_file)

    # import here so the env variables are loaded before the initialization of the db client (which uses them to connect)
    from application.use_cases.transformation.main import transform_sources
    from infrastructure.config import PipelineConfig
    from infrastructure.db.repositories import from_config

    config = PipelineConfig.from_env()
    repos = from_config(config)

    # Transform the sources ---------------------------------------------------
    if 'all' in args.sources:
        sources = ALL_SOURCES
    else: 
        sources = args.sources

    # check that all sources are valid
    for source in sources:
        if source not in ALL_SOURCES:
            logger.error(f"Invalid source: {source}. The posiblities are: bioconda, bioconda_recipes, github, biotools, bioconductor, galaxy_metadata, toolshed, galaxy, sourceforge and opeb_metrics.")
            logger.info("Transformation aborted because invalid sources were provided.")
            return
    
    logger.info(f"Sources to transform: {sources}")

    # Compute the incremental cutoff here, at the CLI layer, so nothing below
    # adapters/ has to deal with clocks or config. A non-positive window means
    # "no date filter" -> full re-transform.
    if args.updated_within_days > 0:
        updated_since = datetime.now() - timedelta(days=args.updated_within_days)
        logger.info(
            f"Transforming entries updated since {updated_since.isoformat()} "
            f"(last {args.updated_within_days} days)"
        )
    else:
        updated_since = None
        logger.info("Full re-transform (no date filter)")

    logger.info("Transforming raw data...")

    transform_sources(sources=sources, config=config, repos=repos, updated_since=updated_since)

    # Finish ------------------------------------------------------------------
    logger.info("Transformation finished!")

if __name__ == "__main__":
    main()