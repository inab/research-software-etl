from src.application.use_cases.integration.update_all_disambiguation_after_human_resolution import run_disambiguation_after_human_annotation
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

    conflict_blocks_file = args.conflict_blocks_file
    disambiguated_blocks_file = args.disambiguated_blocks_file

    print(f"Conflict blocks file: {conflict_blocks_file}")
    print(f"Disambiguated blocks file: {disambiguated_blocks_file}")

    run_disambiguation_after_human_annotation(conflict_blocks_file, disambiguated_blocks_file)

    print("Disambiguation process finished!")


if __name__ == "__main__":
    main()