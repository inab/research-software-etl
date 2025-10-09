from src.application.services.integration.disambiguation.results import build_disambiguated_record_after_human
from src.application.services.integration.disambiguation.utils import load_dict_from_jsonl, update_jsonl_record
import json


def run_disambiguation_after_human_annotation(
    conflict_blocks_file, 
    disambiguated_blocks_file):

    print('Stating update of disambiguated blocks after human resolution....')


    # Load input data
    disambiguated_blocks = load_dict_from_jsonl(disambiguated_blocks_file)
    conflict_blocks = load_dict_from_jsonl(conflict_blocks_file)


    # Takes the decision from the human annotations file 
    human_log_path = 'human_annotations/human_conflicts_log.jsonl'
    human_annotations = load_dict_from_jsonl(human_log_path)
    conflicts = 0

    for conflict_id in disambiguated_blocks.keys():

        not_found = []

        if disambiguated_blocks[conflict_id].get("resolution") != "manual_review_pending":
            #print(f"Conflict ID {conflict_id} has already been resolved. Skipping.")
            continue
        
        # FUTUTRE> get ids of the human annotation from the disambiguated block, bc there may be more than 1 pair

        # Check if the conflict ID exists in the human annotations
        decision = human_annotations.get(conflict_id)

        if decision:

            # Generate record for disambiguated_blocks.json
            conflict = conflict_blocks.get(conflict_id)
            #print("Conflict:")
            #print(conflict)

            record = build_disambiguated_record_after_human(conflict_id, conflict, decision)

            # Update the disambiguated_blocks.json file. There is already a record for this conflict, so we need to update it
            update_jsonl_record(disambiguated_blocks_file, conflict_id, record)

            conflicts += 1

            #print(f"Updated disambiguated record for conflict ID: {conflict_id}")

        else:
            print(f"Could not found decision of {conflict_id}")
            print(decision)
            # If the conflict ID is not found in the human annotations, add it to the not_found list
            not_found.append(conflict_id)

    print(f"Total conflicts updated: {conflicts}")
    print(f"Total conflicts not found in human annotations: {len(not_found)}")
    print(f"List of conflicts not found in human annotations: {not_found}")