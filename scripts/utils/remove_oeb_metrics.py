# OPEB metrics contribute nothing to the model and are not used in any way. Publications are already in other entries from OEB. 
# this script removes them from the blocks
import json
import sys 
import argparse

def remove_opeb_metrics_entries_verbose(grouped_entries):
    """
    Remove instances from grouped entries where source contains
    'opeb_metrics', 'opeb_metris', or 'bioconda'.

    Prints diagnostics about full group removals and partial cleanings.

    Args:
        grouped_entries (dict): grouped_entries loaded from JSON

    Returns:
        dict: cleaned grouped_entries
    """
    sources_to_remove = {"opeb_metrics", "bioconda"}

    cleaned_grouped = {}
    fully_removed_groups = 0
    partially_cleaned_groups = 0
    total_groups = len(grouped_entries)

    for group_key, group_data in grouped_entries.items():
        instances = group_data.get("instances", [])

        filtered_instances = [
            inst for inst in instances
            if not any(
                source.lower() in sources_to_remove
                for source in inst.get("data", {}).get("source", [])
                if isinstance(source, str)
            )
        ]

        if not filtered_instances:
            fully_removed_groups += 1
            # print(f"❌ Group '{group_key}' removed entirely (only unwanted sources).")
        else:
            if len(filtered_instances) < len(instances):
                partially_cleaned_groups += 1
                # print(f"⚠️ Group '{group_key}' partially cleaned: {len(instances) - len(filtered_instances)} entries removed.")
            cleaned_grouped[group_key] = {"instances": filtered_instances}

    print("\n✅ Cleaning summary:")
    print(f"- Total groups before cleaning: {total_groups}")
    print(f"- Groups fully removed: {fully_removed_groups}")
    print(f"- Groups partially cleaned: {partially_cleaned_groups}")
    print(f"- Total groups after cleaning: {len(cleaned_grouped)}")

    return cleaned_grouped



def main():
    parser = argparse.ArgumentParser(
        description="Remove 'opeb_metrics' instances from grouped software entries"
    )
    parser.add_argument(
        "--in",
        dest="input_file",
        required=True,
        help="Input JSON file with grouped entries",
    )
    parser.add_argument(
        "--out",
        dest="output_file",
        required=True,
        help="Output JSON file for cleaned grouped entries",
    )

    args = parser.parse_args()

    # Load input
    try:
        with open(args.input_file, "r", encoding="utf-8") as f:
            grouped_entries = json.load(f)
    except Exception as e:
        print(f"❌ Failed to read input file: {e}", file=sys.stderr)
        sys.exit(1)

    # Process
    cleaned_grouped = remove_opeb_metrics_entries_verbose(grouped_entries)

    # Write output
    try:
        with open(args.output_file, "w", encoding="utf-8") as f:
            json.dump(cleaned_grouped, f, indent=2)
    except Exception as e:
        print(f"❌ Failed to write output file: {e}", file=sys.stderr)
        sys.exit(1) 



if __name__ == "__main__":
    main()


    '''old
    # Load your grouped entries
    with open("scripts/data/grouped_entries_0.4.json", "r") as f:
        grouped_entries = json.load(f)

    # Clean them
    cleaned_entries = remove_opeb_metrics_entries_verbose(grouped_entries)

    # Save to a new file
    with open("scripts/data/grouped_entries_no_opeb_0.4.json", "w") as f:
        json.dump(cleaned_entries, f, indent=2)
    '''