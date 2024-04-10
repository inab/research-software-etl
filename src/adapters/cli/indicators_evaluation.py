"""
The command-line interface for the integration
"""

from .....FAIRsoft.FAIRsoft.indicators_evaluation.FAIR_indicators_eval import connect_to_db, computeScores, push_to_db
import argparse
import logging
from dotenv import load_dotenv
# assuming loglevel is bound to the string value obtained from the
# command line argument. Convert to upper case to allow the user to
# specify --log=DEBUG or --log=debug

def main():
    parser = argparse.ArgumentParser(
        description="FAIRsoft evaluation of Software Metadata."
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

    logging.info("Evaluation starting...")

    tools, fair = connect_to_db()
    indicators_scores = computeScores(tools)

    push_to_db(indicators_scores, fair)
    logging.info("Evaluation successful!")

if __name__ == "__main__":
    main()