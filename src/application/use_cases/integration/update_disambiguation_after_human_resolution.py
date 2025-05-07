from src.application.services.integration.disambiguation.results import build_disambiguated_record_after_human
import json


async def run_disambiguation_after_human_annotation(
    conflict_id,
    conflict_blocks_file, 
    disambiguated_blocks_file):

    print(f"Conflict ID: {conflict_id}")


    # Load input data
    with open(conflict_blocks_file, 'r') as f:
        conflict_blocks = json.load(f)


    # Takes the decision from the human annotations file 
    human_log_path = 'human_annotations/human_conflicts_log.json'
    with open(human_log_path, 'r') as f:
        human_annotations = json.load(f)

    decision = human_annotations.get(conflict_id)
    print("Decision")
    print(decision)

    # Generate record for disambiguated_blocks.json
    conflict = conflict_blocks.get(conflict_id)
    print("Conflict:")
    print(conflict)

    record = build_disambiguated_record_after_human(conflict_id, conflict, decision)

    # Update the disambiguated_blocks.json file. There is already a record for this conflict, so we need to update it

    with open(disambiguated_blocks_file, 'r+') as f:
        disambiguated_blocks = json.load(f)
        disambiguated_blocks.update(record)
        f.seek(0)
        json.dump(disambiguated_blocks, f, indent=2)
        f.truncate()


