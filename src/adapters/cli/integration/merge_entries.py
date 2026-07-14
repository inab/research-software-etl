import argparse
import logging
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

    identities = summary.get("identities")
    if identities:
        print('----------- Identities ----------')
        print(f"Kept the id of the tool they continue: {identities['preserved']}")
        print(f"New tools (no ancestor):               {identities['new']}")
        print(f"Retired ids (no successor):            {identities['retired']}")
        if identities['contested']:
            print(
                f"Contested:                             {identities['contested']}"
                "  (oldest ancestor won over a larger-overlap one)"
            )
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
        "--run-id",
        help=(
            "Identifier of this run. Names the archive the live tools collection is "
            "moved to when the run is promoted, so `rsetl rollback <run-id>` can undo it."
        ),
        type=str,
        dest="run_id",
        required=True,
    )

    parser.add_argument(
        "--no-promote",
        help=(
            "Build the staging collection but do not swap it in. Leaves the live tools "
            "collection untouched; promote later, or inspect the staging collection first."
        ),
        action="store_true",
        dest="no_promote",
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

    from application.use_cases.integration.finalize_run import finalize_run
    from application.use_cases.integration.merge_entries import merge_and_save_blocks
    from infrastructure.config import PipelineConfig
    from infrastructure.db.repositories import Repositories

    config = PipelineConfig.from_env(
        disambiguated_blocks_path=args.disambiguated_blocks_file
    )
    repos = Repositories.from_config(config)

    logger.info(f"Disambiguated blocks file: {config.disambiguated_blocks_path}")
    logger.info("Merging entries...")
    summary = merge_and_save_blocks(config.disambiguated_blocks_path, repos)
    print_summary(summary)

    if args.no_promote:
        logger.info(
            "Built '%s'. Not promoting (--no-promote); '%s' is unchanged.",
            config.tools_staging_collection,
            config.tools_collection,
        )
        return

    result = finalize_run(args.run_id, config, repos)
    print(f"Promoted {config.tools_staging_collection} -> {result['promoted']}")
    if result["archived_as"]:
        print(f"Previous collection archived as {result['archived_as']}")
        print(f"To undo: rsetl rollback {args.run_id}")
    logger.info("Merging finished!")

if __name__ == "__main__":
    main()
