"""
The command-line interface for the transformer
"""

from src.application.use_cases.transformation.main import transform_sources
import argparse
import logging
from dotenv import load_dotenv
# assuming loglevel is bound to the string value obtained from the
# command line argument. Convert to upper case to allow the user to
# specify --log=DEBUG or --log=debug

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
        "--loglevel", "-l",
        help=("Set the logging level"),
        default="INFO",
    )

    args = parser.parse_args()

    load_dotenv(args.env_file)

    numeric_level = getattr(logging, args.loglevel.upper())
    logging.basicConfig(level=numeric_level)
    logging.debug(f"Env file: {args.env_file}")

    logging.info("Transforming raw data...")

    # COULD DO: take sources from argparse
    #sources = ['bioconda', 'biotools', 'bioconductor', 'galaxy_metadata', 'toolshed', 'galaxy', 'sourceforge', 'opeb_metrics']
    sources = ['bioconda']
    transform_sources(loglevel=numeric_level, sources=sources)
    logging.info("Transformation successful!")

if __name__ == "__main__":
    main()