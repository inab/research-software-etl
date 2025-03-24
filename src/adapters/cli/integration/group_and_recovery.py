"""
The command-line interface for the group and recovery step of the integration 
""" 
import argparse
import logging
from dotenv import load_dotenv
from src.application.use_cases.integration.group_and_recovery import grouping_and_recovery_process 

logger = logging.getLogger("rs-etl-pipeline")

def main():
    parser = argparse.ArgumentParser(
        description="""Group entries based on shared repository links and shared name and non-repository links. Entries, that must have been previously standardized,
        are fetched from the MongoDB database. The grouped entries are written to a JSON file."""
    )

    parser.add_argument(
        "--grouped-entries-file", "-g",
        help=("Path to the file containing grouped entries. This file is the output of the whole process. Default is 'data/grouped.json'."),
        type=str,
        dest="grouped_entries_file",
        default="data/grouped.json",
    )

    parser.add_argument(
        "--env-file", "-e",
        help=("File containing environment variables to be set before running "),
        type=str,
        dest="env_file",
        default=".env",
    )

    args = parser.parse_args()

    load_dotenv(args.env_file)


    logger.debug(f"Grouped entries file: {args.grouped_entries_file}")
    logger.debug(f"Env file: {args.env_file}")

    logger.info("Grouping entries and recovering shared entries...")
    grouping_and_recovery_process(args.grouped_entries_file)

    logger.info("Grouping and recovery finished!")


if __name__ == "__main__":
    main()