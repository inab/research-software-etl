from src.application.services.integration.disambiguation.utils import load_dict_from_jsonl, add_jsonl_record, update_jsonl_record
from datetime import datetime
import json
from pprint import pprint



def generate_secondary_conflicts(disambiguated_blocks):
    """
    Create new conflict blocks from unresolved entries in disambiguated_blocks.
    """
    secondary_conflict = {}
    secondary_block = {}
    secondary_counter = 0

    for parent_id, record in disambiguated_blocks.items():
        unmerged = record.get("unmerged_entries", [])
        resolution = record.get("resolution", None)
        if len(unmerged) > 1 and resolution!= "manual_review_pending":
            
            secondary_counter += 1
            new_id = f"{parent_id}_secondary_{secondary_counter}"
            secondary_conflict[new_id] = {
                "remaining": [{"id": unmerged[0]}],  # use first as reference
                "disconnected":  [{"id": entry} for entry in unmerged[1:]],
                "parent_block_id": parent_id,
                "generated_at": datetime.now().isoformat()
            }

            secondary_block[new_id] = {
                "instances": [{"_id": entry} for entry in unmerged],
                "parent_block_id": parent_id,
                "generated_at": datetime.now().isoformat()
            }

    return secondary_conflict, secondary_block




async def run_second_round(conflict_blocks_path, disambiguated_blocks_path, blocks, blocks_path, disambiguate_blocks_func):
    """
    Loads existing disambiguation results and conflict blocks,
    generates second-round conflicts, and runs disambiguation again.
    """
    # Load files
    disambiguated_blocks = load_dict_from_jsonl(disambiguated_blocks_path)
    conflict_blocks = load_dict_from_jsonl(conflict_blocks_path)


    # Generate secondary conflict blocks
    secondary_conflict, secondary_block = generate_secondary_conflicts(disambiguated_blocks)

    if not secondary_conflict:
        print("No secondary conflicts to process.")
        return disambiguated_blocks

    # Update conflict_blocks.json and  blocks with secondary round blocks
    conflict_blocks.update(secondary_conflict)
    blocks.update(secondary_block)


    for key in secondary_conflict:
        update_jsonl_record(conflict_blocks_path, key, secondary_conflict)
        update_jsonl_record(blocks_path, key, secondary_block)

    print(f"🔁 {len(secondary_conflict)} secondary conflict blocks generated and added.")

    # Re-run disambiguation on new conflicts
    updated_disambiguated_blocks = await disambiguate_blocks_func(conflict_blocks, blocks, disambiguated_blocks_path)

    print("✅ Second round of disambiguation completed.")
    return updated_disambiguated_blocks

