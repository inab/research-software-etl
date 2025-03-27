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

"""
import argparse
import logging
from dotenv import load_dotenv
from src.infrastructure.logging_config import setup_logging

# assuming loglevel is bound to the string value obtained from the
# command line argument. Convert to upper case to allow the user to
# specify --log=DEBUG or --log=debug

logger = setup_logging()

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
        description=""
    )
    parser.add_argument(
        "--env-file", "-e",
        help=("File containing environment variables to be set before running "),
        default=".env",
    )

    parser.add_argument(
        "--sources-to-transform", "-s",
        help=("Sources to transform. The posiblities are: bioconda, bioconda_recipes, github, biotools, bioconductor, galaxy_metadata, toolshed, galaxy, sourceforge and opeb_metrics, or all to include all of them. Default is all sources."),
        nargs='+',
        default=['all'],
        dest="sources"
    )

    args = parser.parse_args()

    # Load the environment variables ------------------------------------------
    logger.debug(f"Env file: {args.env_file}")
    load_dotenv(args.env_file)

    # import here so the env variables are loaded before the initialization of the db client (which uses them to connect)
    from src.application.use_cases.transformation.main import transform_sources
    
    # Transform the sources ---------------------------------------------------
    logger.info(f"Sources to transform: {args.sources}")
    if 'all' in args.sources:
        args.sources = ALL_SOURCES
    else: 
        sources = args.sources

    logger.info("Transforming raw data...")

    transform_sources(sources=sources)

    # Finish ------------------------------------------------------------------
    logger.info("Transformation finished!")

if __name__ == "__main__":
    main()