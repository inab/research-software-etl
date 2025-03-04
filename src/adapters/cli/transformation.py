"""
The command-line interface for the transformer
"""
import argparse
import logging
from dotenv import load_dotenv
from src.application.use_cases.transformation.main import transform_sources
from src.infrastructure.logging_config import setup_logging

# assuming loglevel is bound to the string value obtained from the
# command line argument. Convert to upper case to allow the user to
# specify --log=DEBUG or --log=debug

logger = setup_logging()

def main():
    parser = argparse.ArgumentParser(
        description=""
    )
    parser.add_argument(
        "--env-file", "-e",
        help=("File containing environment variables to be set before running "),
        default=".env",
    )

    args = parser.parse_args()

    load_dotenv(args.env_file)

    logger.debug(f"Env file: {args.env_file}")

    logger.info("Transforming raw data...")

    # COULD DO: take sources from argparse
    sources = ['bioconda', 'github', 'biotools', 'bioconductor', 'galaxy_metadata', 'toolshed', 'galaxy', 'sourceforge', 'opeb_metrics']
    
    transform_sources(sources=sources)
    logger.info("Transformation successful!")

if __name__ == "__main__":
    main()