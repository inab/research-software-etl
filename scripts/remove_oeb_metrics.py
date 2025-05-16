# OPEB metrics contribute nothing to the model and are not used in any way. Publications are already in other entries from OEB. 
# this script removes them from the blocks
import json

def remove_opeb_metrics_entries_verbose(grouped_entries):
    """
    Remove instances from grouped entries where source contains 'opeb_metrics'.
    Prints diagnostics about full group removals and partial cleanings.
    
    Args:
        grouped_entries (dict): grouped_entries loaded from JSON
    
    Returns:
        dict: cleaned grouped_entries
    """
    cleaned_grouped = {}
    fully_removed_groups = 0
    partially_cleaned_groups = 0
    total_groups = len(grouped_entries)

    for group_key, group_data in grouped_entries.items():
        instances = group_data.get("instances", [])
        filtered_instances = [
            inst for inst in instances
            if not any(source.lower() == "opeb_metrics" for source in inst.get("data", {}).get("source", []))
        ]

        if not filtered_instances:
            fully_removed_groups += 1
            print(f"❌ Group '{group_key}' removed entirely (only 'opeb_metrics' entries).")
        else:
            if len(filtered_instances) < len(instances):
                partially_cleaned_groups += 1
                print(f"⚠️ Group '{group_key}' partially cleaned: {len(instances) - len(filtered_instances)} entries removed.")
            cleaned_grouped[group_key] = {"instances": filtered_instances}

    print("\n✅ Cleaning summary:")
    print(f"- Total groups before cleaning: {total_groups}")
    print(f"- Groups fully removed: {fully_removed_groups}")
    print(f"- Groups partially cleaned: {partially_cleaned_groups}")
    print(f"- Total groups after cleaning: {len(cleaned_grouped)}")

    return cleaned_grouped

if __name__ == "__main__":
    # Load your grouped entries
    with open("scripts/data/grouped_entries.json", "r") as f:
        grouped_entries = json.load(f)

    # Clean them
    cleaned_entries = remove_opeb_metrics_entries_verbose(grouped_entries)

    # Save to a new file
    with open("scripts/data/grouped_entries_no_opeb.json", "w") as f:
        json.dump(cleaned_entries, f, indent=2)