
import json 
from application.services.integration.disambiguation.secondary_round import run_second_round
from application.services.integration.disambiguation.disambiguator import disambiguate_blocks 
from application.services.integration.disambiguation.utils import load_dict_from_jsonl
from pprint import pprint

async def run_full_disambiguation(blocks_file, 
                         conflict_blocks_file, 
                         disambiguated_blocks_file,
                         pair_wise_decisions_file,
                         run_id):

    # 1. Load input data

    blocks = load_dict_from_jsonl(blocks_file)
    conflict_blocks = load_dict_from_jsonl(conflict_blocks_file)


    # 3. Run first round of disambiguation

    disambiguated_blocks = await disambiguate_blocks(
        conflict_blocks=conflict_blocks,
        blocks=blocks,
        disambiguated_blocks_path=disambiguated_blocks_file,
        pair_wise_decisions_path=pair_wise_decisions_file,
        run_id=run_id
    )


    unresolved_keys = [k for k in conflict_blocks if k not in disambiguated_blocks]

    print(f"{len(unresolved_keys)} unresolved keys.")
    print(f"Unresolved keys :")
    if len(unresolved_keys)>0:
        for item in unresolved_keys:
            print(item)
    print("# -------------------------------------")

    # 4. Repeat second-round disambiguation until everything is resolved
    rounds_n = 0
    while len(unresolved_keys)>0 and rounds_n<5:
        rounds_n += 1
        # Run a second (or N-th) round
        # conflict_blocks_path, disambiguated_blocks_path, blocks, blocks_path, disambiguate_blocks_func
        disambiguated_blocks = await run_second_round(
            conflict_blocks_path=conflict_blocks_file,
            disambiguated_blocks_path=disambiguated_blocks_file,
            blocks=blocks,
            blocks_path=blocks_file,
            run_id=run_id,
            pair_wise_decisions_path=pair_wise_decisions_file,
            disambiguate_blocks_func=disambiguate_blocks
        )

        # Reload conflict_blocks to see what's left
        conflict_blocks = load_dict_from_jsonl(conflict_blocks_file)

        unresolved_keys = [k for k in conflict_blocks if k not in disambiguated_blocks]

        if not unresolved_keys:
            print("✨All conflicts resolved.")
            break
        else:
            print(f"{len(unresolved_keys)} unresolved blocks remain. Continuing...")

    print(' ----------- Disambiguation ended ----------------------')
    print(f"Disambiguation exited unfinished after {rounds_n} second rounds.")
    print(f"Number of unresolved keys: {len(unresolved_keys)}")
    if len(unresolved_keys)>0:
        print(f"Unresolved keys: {','.join(unresolved_keys)}")
    print('--------------------------------------------------------')

    
