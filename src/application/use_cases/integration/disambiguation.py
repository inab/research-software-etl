
import json 
from src.application.services.integration.disambiguation.secondary_round import disambiguate_blocks, run_second_round

def build_instances_keys_dict(data):
    """Create a mapping of instance IDs to their respective instance data."""
    instances_keys = {}
    for key, value in data.items():
        instances = value.get("instances", [])
        for instance in instances:
            instances_keys[instance["_id"]] = instance
    return instances_keys

def run_full_disambiguation(grouped_entries_file, 
                         disconnected_entries_file, 
                         disambiguated_blocks_file, 
                         instances_dict_file):

    # 1. Load input data
    with open(grouped_entries_file, 'r') as f:
        blocks = json.load(f)

    with open(disconnected_entries_file, 'r') as f:
        conflict_blocks = json.load(f)


    # 2. Run first round of disambiguation
    disambiguated_blocks = {}

    disambiguated_blocks = disambiguate_blocks(
        conflict_blocks=conflict_blocks,
        blocks=blocks,
        disambiguated_blocks=disambiguated_blocks
    )

    # 3. Save disambiguated_blocks after first round
    with open(disambiguated_blocks_file, 'w') as f:
        json.dump(disambiguated_blocks, f, indent=2)

    # 4. Repeat second-round disambiguation until everything is resolved
    while True:
        # Run a second (or N-th) round
        disambiguated_blocks = run_second_round(
            conflict_blocks_path=disconnected_entries_file,
            disambiguated_blocks_path=disambiguated_blocks_file,
            blocks=blocks,
            disambiguate_blocks_func=disambiguate_blocks
        )

        # Reload conflict_blocks to see what's left
        with open(disconnected_entries_file, 'r') as f:
            conflict_blocks = json.load(f)

        unresolved_keys = [k for k in conflict_blocks if k not in disambiguated_blocks]

        if not unresolved_keys:
            print("✨All conflicts resolved.")
            break
        else:
            print(f"🔁 {len(unresolved_keys)} unresolved blocks remain. Continuing...")

