import datetime
import json



def generate_secondary_conflicts(disambiguated_blocks, threshold=0.85):
    """
    Create new conflict blocks from unresolved entries in disambiguated_blocks.
    """
    secondary_blocks = {}
    secondary_counter = 0

    for parent_id, record in disambiguated_blocks.items():
        unmerged = record.get("unmerged_entries", [])
        if len(unmerged) > 1:
            for i in range(1, len(unmerged)):
                secondary_counter += 1
                new_id = f"{parent_id}_secondary_{secondary_counter}"
                secondary_blocks[new_id] = {
                    "remaining": [{"id": unmerged[0]}],  # use first as reference
                    "disconnected": [{"id": unmerged[i]}],
                    "parent_block_id": parent_id,
                    "generated_at": datetime.utcnow().isoformat()
                }

    return secondary_blocks


def run_second_round(conflict_blocks_path, disambiguated_blocks_path, blocks, disambiguate_blocks_func):
    """
    Loads existing disambiguation results and conflict blocks,
    generates second-round conflicts, and runs disambiguation again.
    """
    # Load files
    with open(disambiguated_blocks_path, "r") as f:
        disambiguated_blocks = json.load(f)

    with open(conflict_blocks_path, "r") as f:
        conflict_blocks = json.load(f)

    # Generate secondary conflict blocks
    secondary_blocks = generate_secondary_conflicts(disambiguated_blocks)

    if not secondary_blocks:
        print("No secondary conflicts to process.")
        return disambiguated_blocks

    # Update conflict_blocks.json with secondary round blocks
    conflict_blocks.update(secondary_blocks)

    with open(conflict_blocks_path, "w") as f:
        json.dump(conflict_blocks, f, indent=2)

    print(f"🔁 {len(secondary_blocks)} secondary conflict blocks generated and added.")

    # Re-run disambiguation on new conflicts
    updated_disambiguated_blocks = disambiguate_blocks_func(conflict_blocks, blocks, disambiguated_blocks)

    # Save updated disambiguated_blocks.json
    with open(disambiguated_blocks_path, "w") as f:
        json.dump(updated_disambiguated_blocks, f, indent=2)

    print("✅ Second round of disambiguation completed.")
    return updated_disambiguated_blocks

