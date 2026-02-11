from src.application.services.integration.disambiguation.pairing import build_pairs
from src.application.services.integration.disambiguation.conflict_builder import build_full_conflict
from src.application.services.integration.disambiguation.prompts import build_prompt
from src.application.services.integration.disambiguation.proxy import decision_agreement_proxy
from src.application.services.integration.disambiguation.results import build_disambiguated_record, build_disambiguated_record_manual, build_no_conflict_record
from src.application.services.integration.disambiguation.issues import create_github_issue, generate_github_body, generate_context, generate_conflict_file, commit_conflict_json
from src.application.services.integration.disambiguation.utils import replace_with_full_entries, filter_relevant_fields, build_instances_keys_dict, load_dict_from_jsonl, add_jsonl_record, load_pair_decisions, stable_hash, append_dict_to_jsonl
from src.application.services.integration.disambiguation.manual_annotation_lookup import find_previous_annotation_for_conflict
from src.application.services.integration.disambiguation.results import build_disambiguated_record_after_human

import json 
import logging 
import os
import copy


from pprint import pprint
from datetime import datetime, timezone



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




def build_record_from_legacy():
    "Buils the record to put in disambiguted_blocks if this disambiguation was already done"
    pass 

PAIR_DECISIONS_PATH = "/Users/evabsc/projects/software-observatory/research-software-etl/src/application/services/integration/disambiguation/pair_decisions.jsonl"

async def process_conflict(conflict_name, conflict, instances_dict, run_id, best_pair):
    """
    Process a single conflict block: build pairs, disambiguate them, and return
    a disambiguated_blocks record for this block.
    """
    
    # Replace summary info with full entries
    conflict_full = replace_with_full_entries(conflict, instances_dict)

    # Build disambiguation pairs
    conflict_pairs, _ = build_pairs(copy.deepcopy(conflict_full), conflict_name, more_than_two_pairs=0)

    pair_results = []
    n = 0
    for conflict_pair in conflict_pairs:

        #print("Processing conflict pair:")
        #pprint(conflict_pair)
        
        # ------------- ID ----------------
        n+= 1
        pair_stable_id = f"p:{conflict_name}_{stable_hash(conflict_pair)}"
        #pair_stable_id = f"p:{conflict_name}"
        # ---------------------------------

        # ----- check for best pair --------
        if pair_stable_id in best_pair:
            decision = best_pair[pair_stable_id]
            pair_results.append({
                "remaining_id": conflict_pair["remaining"][0]["_id"], 
                "disconnected_id": conflict_pair["disconnected"][0]["_id"],
                "same_as_remaining": decision.get('same_as_remaining'),
                "confidence": decision.get('confidence'),
                "conflict_id": pair_stable_id,
                "source":"llm",
                'ts':  decision.get('ts')
            })

            continue


        # -----------------------------------
        # Prepare enriched entry for disambiguation
        full_conflict = filter_relevant_fields(conflict_pair)
        full_conflict = await build_full_conflict(full_conflict)

        # ---- LLM-based decison ----------
 
        # Generate prompt and run model
        messages = build_prompt(full_conflict["disconnected"], full_conflict["remaining"])
        result = decision_agreement_proxy(messages)

        # Log the result
        add_jsonl_record("scripts/data/results_proxy.jsonl", { conflict_name: result })
        
        # Model made a decision 
        if result.get("verdict") != "disagreement":
            # ----- Add to pair decisions file -----------
            payload = {
                "pair_id": pair_stable_id,
                "kind": 'pair',
                "same_as_remainging": result["verdict"].lower() == "same",
                "confidence": "",
                "source": 'llm',
                "ts": datetime.now(timezone.utc).isoformat()
            }
            append_dict_to_jsonl(PAIR_DECISIONS_PATH, payload)


            # ----- Add to results -----------

            pair_results.append({
                "remaining_id": conflict_pair["remaining"][0]["_id"], # replace with conflict_pair["remaining"][0]["id"]
                "disconnected_id": conflict_pair["disconnected"][0]["_id"], # replace with conflict_pair["disconnected"][0]["id"]
                "same_as_remaining": result["verdict"].lower() == "same",
                "confidence": result.get("confidence", None),
                "conflict_id": pair_stable_id,
                "source":"llm",
                'ts':  datetime.now(timezone.utc).isoformat()
            })

        # ------------------------------------

        else:

            # ----------------------- Human-based decision ------------------------

            # this log file will be replaced by pair_wise_cache.jsonl
            HUMAN_LOG_PATH = "/Users/evabsc/projects/software-observatory/research-software-etl/human_annotations/human_conflicts_log.jsonl"
            decision = find_previous_annotation_for_conflict(conflict_pair, HUMAN_LOG_PATH)

            # TODO LATER: more than one pair may need disambiguation, so we need a way to differentiate them 
            if decision:
                decision.pop("conflict", None)
                record = build_disambiguated_record_after_human(conflict_name, conflict_pair, decision)
                pair_results.append(record)
                

            else:
                ## conflict file creation
                content, filename = generate_conflict_file(conflict_pair, conflict_name, pair_stable_id, run_id)
                path = f"human_annotations/conflicts/{filename}"
                conflict_url = commit_conflict_json(content, path)

                ## issue creation
                context = generate_context(conflict_name, pair_stable_id, full_conflict, conflict_url, run_id)
                body = generate_github_body(context)
                
                title = f"Manual resolution needed for {conflict_name}_pair_{n}"
                labels = ['conflict', 'automated']
                #response = create_github_issue(title, body, labels)
                print(f'Github issue for {conflict_name}_pair_{n}')
                response = {
                    'html_url' : 'dry_run'
                }
                # record event to results
                # add conflict id to disambiguated record (disambiguated_blocks file)
                return build_disambiguated_record_manual(conflict_name, conflict, response["html_url"])
        

    # Build final record
    return build_disambiguated_record(conflict_name, conflict, pair_results)




async def disambiguate_blocks(conflict_blocks, blocks, disambiguated_blocks_path, pair_wise_decisions_path, run_id):
    '''
    Disambiguated blocks can be empty at the beginning.
    The function will fill it with the disambiguated entries.
    '''
    disambiguated_blocks = load_dict_from_jsonl(disambiguated_blocks_path)
    instances_dict = build_instances_keys_dict()
    # best_pair maps each pair_key to the single highest-priority decision (human > LLM, otherwise most informed / recent).
    best_pair = load_pair_decisions(pair_wise_decisions_path)  
    n=0

    for key in blocks:
        n+=1
        if n%1000==0:
            print(f"Processed {n} blocks.\n")
        if key not in disambiguated_blocks:
            #print(f"Processing block: {key}")
            record = {}
            if key in conflict_blocks:
                #print(f"{key} is a conflict block")

                if key not in disambiguated_blocks:
                    #print(f"{key} not in disambiguated blocks")
                    try:
                        record = await process_conflict(key, conflict_blocks[key], instances_dict, run_id, best_pair)
                        disambiguated_blocks.update(record)
                    except Exception as e:
                        print(f"Error processing conflict {key}")
                        logging.error(f"Error processing conflict {key}: {e}")
                        
            else:
                record = build_no_conflict_record(key, blocks[key])
                disambiguated_blocks.update(record)
                #print(f"{key} is not a conflict block")

            if record:
                add_jsonl_record(disambiguated_blocks_path, record)

        else:
            #print(f"Record {key} already exists in disambiguated blocks, skipping...")
            pass

    return disambiguated_blocks



