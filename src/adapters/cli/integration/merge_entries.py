import argparse
import logging
from dotenv import load_dotenv


from dotenv import load_dotenv

logger = logging.getLogger("rs-etl-pipeline")

def print_summary(summary):

    print("✨ Merging completed! ✨")
    print('----------- Summary -------------')
    print(f"Iterated over {summary['N']} blocks.")
    print(f" |")
    print(f" |-- Processed {summary['n_processed']} blocks.")
    print(f" |    |")
    print(f" |    '-- Inserted {summary['n_inserted_entries']} entries in db.")
    print(f" |   ")
    print(f" '-- Still {summary['N'] - summary['n_processed']} blocks pending.")
    print(f"     |")
    print(f"     '-- For human review: {summary['n_pending']}")
    print(f"     |")
    print(f"     '-- Unclear for human: {summary['n_unclear']}")
    print('---------------------------------')


def main():
    parser = argparse.ArgumentParser(
        description="""Merge records in resolved blocks and save to database."""
    )

    parser.add_argument(
        "--disambiguated-blocks-file", "-n",
        help=("Path to the file where the disambiguated grouped entries and all other groups will be written. Default is 'data/disambiguated_grouped.json'."),
        type=str,
        dest="disambiguated_blocks_file"
    )

    parser.add_argument(
        "--env-file", "-e",
        help=("File containing environment variables to be set before running "),
        default=".env",
    )

    args = parser.parse_args()

    # Load the environment variables ------------------------------------------
    logger.debug(f"Env file: {args.env_file}")
    load_dotenv(args.env_file)

    from src.application.use_cases.integration.merge_entries import merge_and_save_blocks

    logger.info(f"Disambiguated blocks file: {args.disambiguated_blocks_file}")
    logger.info("Merging entries...")
    summary = merge_and_save_blocks(args.disambiguated_blocks_file)
    print_summary(summary)
    logger.info("Merging finished!")

if __name__ == "__main__":
    main()
