from application.use_cases.integration.update_all_disambiguation_after_human_resolution import run_disambiguation_after_human_annotation
from infrastructure.config import PipelineConfig
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="""Update the disambiguation results after human resolution. The function takes the conflict ID, the path to the conflict blocks file, and the path to the disambiguated blocks file as input. The function updates the disambiguated blocks file with the new record for the given conflict ID."""
    )

    parser.add_argument(
        "--conflict-blocks-file", "-cf",
        help=("Path to the file containing conflict blocks."),
        type=str,
        dest="conflict_blocks_file",
        default="scripts/data/conflict_blocks.jsonl",
    )

    parser.add_argument(
        "--disambiguated-blocks-file", "-df",
        help=("Path to the file containing disambiguated blocks."),
        type=str,
        dest="disambiguated_blocks_file",
        default="scripts/data/disambiguated_blocks.jsonl",
    )

    args = parser.parse_args()

    config = PipelineConfig.from_env(
        conflicts_json_path=args.conflict_blocks_file,
        disambiguated_blocks_path=args.disambiguated_blocks_file,
    )

    print(f"Conflict blocks file: {config.conflicts_json_path}")
    print(f"Disambiguated blocks file: {config.disambiguated_blocks_path}")

    run_disambiguation_after_human_annotation(
        config.conflicts_json_path,
        config.disambiguated_blocks_path,
        config,
    )

    print("Disambiguation process finished!")


if __name__ == "__main__":
    main()