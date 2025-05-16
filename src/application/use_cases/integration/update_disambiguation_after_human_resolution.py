from src.application.services.integration.disambiguation.results import build_disambiguated_record_after_human
from src.application.services.integration.disambiguation.utils import load_dict_from_jsonl, update_jsonl_record
import json


def run_disambiguation_after_human_annotation(
    conflict_id,
    conflict_blocks_file, 
    disambiguated_blocks_file):

    print(f"Conflict ID: {conflict_id}")


    # Load input data
    conflict_blocks = load_dict_from_jsonl(conflict_blocks_file)

    # Takes the decision from the human annotations file 
    human_log_path = 'human_annotations/human_conflicts_log.json'
    human_annotations = load_dict_from_jsonl(human_log_path)

    decision = human_annotations.get(conflict_id)
    print("Decision")
    print(decision)

    # Generate record for disambiguated_blocks.json
    conflict = conflict_blocks.get(conflict_id)
    print("Conflict:")
    print(conflict)

    record = build_disambiguated_record_after_human(conflict_id, conflict, decision)

    # Update the disambiguated_blocks.json file. There is already a record for this conflict, so we need to update it
    update_jsonl_record(disambiguated_blocks_file, conflict_id, record)

