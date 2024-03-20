"""
The command-line interface for the integration
"""

from .run_integration import run_integration
import argparse
import logging
from dotenv import load_dotenv
# assuming loglevel is bound to the string value obtained from the
# command line argument. Convert to upper case to allow the user to
# specify --log=DEBUG or --log=debug

def main():
    parser = argparse.ArgumentParser(
        description="An over-simplified downloader to demonstrate python packaging."
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

    logging.info("Integrating data from sources...")
    run_integration(loglevel=numeric_level)
    logging.info("Integration successful!")

if __name__ == "__main__":
    main()