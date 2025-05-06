from datetime import datetime
import json



def generate_secondary_conflicts(disambiguated_blocks):
    """
    Create new conflict blocks from unresolved entries in disambiguated_blocks.
    """
    secondary_conflict = {}
    secondary_block = {}
    secondary_counter = 0

    for parent_id, record in disambiguated_blocks.items():
        unmerged = record.get("unmerged_entries", [])
        if len(unmerged) > 1:
            
            secondary_counter += 1
            new_id = f"{parent_id}_secondary_{secondary_counter}"
            secondary_conflict[new_id] = {
                "remaining": [{"id": unmerged[0]}],  # use first as reference
                "disconnected":  [{"id": entry} for entry in unmerged[1:]],
                "parent_block_id": parent_id,
                "generated_at": datetime.now()
            }

            secondary_block[new_id] = {
                "instances": [{"_id": entry} for entry in unmerged],
                "parent_block_id": parent_id,
                "generated_at": datetime.now()
            }

    return secondary_conflict, secondary_block


async def run_second_round(conflict_blocks_path, disambiguated_blocks_path, blocks, blocks_path, disambiguate_blocks_func):
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
    secondary_conflict, secondary_block = generate_secondary_conflicts(disambiguated_blocks)

    if not secondary_conflict:
        print("No secondary conflicts to process.")
        return disambiguated_blocks

    # Update conflict_blocks.json and  blocks with secondary round blocks
    conflict_blocks.update(secondary_conflict)
    blocks.update(secondary_block)

    with open(conflict_blocks_path, "w") as f:
        json.dump(conflict_blocks, f, indent=2)


    with open(blocks_path, "w") as f:
        json.dump(blocks, f, indent=2)
    

    print(f"🔁 {len(secondary_conflict)} secondary conflict blocks generated and added.")

    # Re-run disambiguation on new conflicts
    updated_disambiguated_blocks = await disambiguate_blocks_func(conflict_blocks, blocks, disambiguated_blocks)

    # Save updated disambiguated_blocks.json
    with open(disambiguated_blocks_path, "w") as f:
        json.dump(updated_disambiguated_blocks, f, indent=2)

    print("✅ Second round of disambiguation completed.")
    return updated_disambiguated_blocks

