from src.application.services.integration.disambiguation.pairing import build_pairs
from src.application.services.integration.disambiguation.conflict_builder import build_full_conflict
from src.application.services.integration.disambiguation.prompts import build_prompt
from src.application.services.integration.disambiguation.proxy import decision_agreement_proxy
from src.application.services.integration.disambiguation.results import build_disambiguated_record, build_no_conflict_record
from src.application.services.integration.disambiguation.issues import create_issue, generate_github_issue, generate_context
from src.application.services.integration.disambiguation.utils import replace_with_full_entries, filter_relevant_fields, build_instances_keys_dict
import json 
import logging 
import os


def log_error(conflict):
    with open('data/error_conflicts.json', 'a') as f:
        f.write(json.dumps(conflict, indent=4))


def log_result(result):
    with open('data/results.json', 'a') as f:
        f.write(json.dumps(result, indent=4))
    logging.info("Result logged")


def write_to_results_file(result, results_file):
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, "a") as f:
            json.dump(result, f)
            f.write("\n")
    except Exception as e:
        logging.error(f"Error writing to results file: {e}")

def load_solved_conflict_keys(jsonl_path):
    solved_keys = set()
    if not os.path.exists(jsonl_path):
        return solved_keys
    with open(jsonl_path, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    entry = json.loads(line)
                    key = next(iter(entry))
                    solved_keys.add(key)
                except Exception as e:
                    logging.warning(f"Could not parse line: {line[:100]}...\n{e}")
    return solved_keys


async def process_conflict(key, conflict, instances_dict, model_name="auto:mistral-7b"):
    """
    Process a single conflict block: build pairs, disambiguate them, and return
    a disambiguated_blocks record for this block.
    """

    # Replace summary info with full entries
    conflict = replace_with_full_entries(conflict, instances_dict)

    # Build disambiguation pairs
    conflict_pairs, _ = build_pairs(conflict, key, more_than_two_pairs=0)

    pair_results = []

    for conflict_pair in conflict_pairs:
        # Prepare minimal, enriched entry for disambiguation
        full_conflict = filter_relevant_fields(conflict_pair)
        full_conflict = await build_full_conflict(full_conflict)

        # Generate prompt and run model
        messages = build_prompt(full_conflict["disconnected"], full_conflict["remaining"])
        result = decision_agreement_proxy(messages)

        if result.get("verdict") != "disagreement":
            pair_results.append({
                "disconnected_id": full_conflict["disconnected"][0]["id"],
                "same_as_remaining": result["verdict"] == "same",
                "confidence": result.get("confidence", 1.0)
            })
        else:
            # Human fallback
            context = generate_context(key, full_conflict)
            body = generate_github_issue(context, 'github_issue.jinja2')
            title = f"Manual resolution needed for {key}"
            labels = ['conflict']
            # TODO: tigger the issue creation in github
            create_issue(title, body, labels)

    # Build final record
    return build_disambiguated_record(key, conflict, pair_results, model_name)


def load_disambiguated(disambiguated_blocks_path):
    with open(disambiguated_blocks_path, 'r') as f:
        disambiguated_blocks = {}
        for line in f:
            if line.strip():
                try:
                    entry = json.loads(line)
                    key = next(iter(entry))
                    disambiguated_blocks[key] = entry[key]
                except Exception as e:
                    logging.warning(f"Could not parse line: {line[:100]}...\n{e}")
    
    return disambiguated_blocks



async def disambiguate_blocks(conflict_blocks, blocks, disambiguated_blocks_path):
    '''
    Disambiguated blocks can be empty at the beginning.
    The function will fill it with the disambiguated entries.
    '''
    instances_dict = build_instances_keys_dict(blocks)
    disambiguated_blocks = load_disambiguated(disambiguated_blocks_path)

    for key in blocks:
        print(f"Processing block: {key}")
        if key in conflict_blocks:
            print(f"{key} is a conflict block")
            if key not in disambiguated_blocks:
                print(f"{key} not in disambiguated blocks")
                try:
                    record = await process_conflict(key, conflict_blocks[key], instances_dict)
                    disambiguated_blocks.update(record)
                except Exception as e:
                    print(f"Error processing conflict {key}")
                    raise e
                    logging.error(f"Error processing conflict {key}: {e}")
                
        else:
            record = build_no_conflict_record(key, blocks[key])
            disambiguated_blocks.update(record)

    return disambiguated_blocks



