
from src.application.services.integration.disambiguation.secondary_round import run_second_round
from src.application.services.integration.disambiguation.disambiguator import disambiguate_blocks 
import json


async def run_disambiguation(
    blocks_file, 
    conflict_blocks_file, 
    disambiguated_blocks_file,
):
    # Load input data
    with open(conflict_blocks_file, 'r') as f:
        conflict_blocks = json.load(f)

    with open(blocks_file, 'r') as f:
        blocks = json.load(f)

    with open(disambiguated_blocks_file, 'r+') as f:
        disambiguated_blocks = json.load(f)

    # Resume the disambiguation process: second round, etc
    # Repeat second-round disambiguation until everything is resolved
    while True:
        # Run a second (or N-th) round
        # conflict_blocks_path, disambiguated_blocks_path, blocks, blocks_path, disambiguate_blocks_func
        disambiguated_blocks = await run_second_round(
            conflict_blocks_path=conflict_blocks_file,
            disambiguated_blocks_path=disambiguated_blocks_file,
            blocks=blocks,
            blocks_path=blocks_file,
            disambiguate_blocks_func=disambiguate_blocks
        )

        # Reload conflict_blocks to see what's left
        with open(conflict_blocks_file, 'r') as f:
            conflict_blocks = json.load(f)

        unresolved_keys = [k for k in conflict_blocks if k not in disambiguated_blocks]

        if not unresolved_keys:
            print("✨All conflicts resolved.")
            break
        else:
            print(f"🔁 {len(unresolved_keys)} unresolved blocks remain. Continuing...")


