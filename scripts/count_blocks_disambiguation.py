from src.application.services.integration.disambiguation.utils import load_dict_from_jsonl
import json
# ----------------------------------------------------
# Count the number of blocks in the disambiguation process
#
# ----------------------------------------------------


db_pre_human_path = 'scripts/data/disambiguated_blocks_second_round.jsonl'
db_after_human_path = 'scripts/data/disambiguated_blocks.jsonl'

human_solution = 'human_annotations/human_conflicts_log.jsonl'


keys = {}
for line in open(human_solution):
    # load dict from line
    line = line.strip()
    if not line:
        continue
    try:
        d = json.loads(line)
        k = list(d.keys())[0]
        if k in keys:
            print(f"Duplicate key found: {k}")
            keys[k] += 1
        else:
            keys[k] = 1
    except json.JSONDecodeError:
        print(f"Error decoding JSON: {line}")
        continue

for k, v in keys.items():
    if v > 1:
        print(f"Key {k} appears {v} times in the human solution file.")

db_pre_human = load_dict_from_jsonl(db_pre_human_path)

blocks = 0
for k, v in keys.items():
    if k not in db_pre_human:
        print(f"Key {k} not found in the disambiguated blocks file.")
    else:
        blocks += 1
        if db_pre_human[k].get("resolution") != "manual_review_pending":
            print(f"Key {k} is not marked as manual_review_pending in the disambiguated blocks file.")

print(f"Total number of blocks in the human solution file: {len(keys)}")


non_conflictive = 0
conflictive = 0
solved_by_llms = 0
unclear_for_llms = 0
solved_by_human = 0
unclear_for_human = 0



for key in db_pre_human:
    if db_pre_human[key].get("resolution") == "no_conflict":
        non_conflictive += 1
    else:
        if '_secondary_' in key:
            # This is a secondary block, so we don't count it
            continue
        conflictive += 1

        if db_pre_human[key].get("resolution") == "merged" or db_pre_human[key].get("resolution") == "partial":
            solved_by_llms += 1

        elif db_pre_human[key].get("resolution") == "manual_review_pending":
            unclear_for_llms += 1

        else:
            print(f"WARNING: Unknown resolution: {db_pre_human[key].get('resolution')}.")
            unclear_for_llms += 1


db_after_human = load_dict_from_jsonl(db_after_human_path)
for key in db_after_human:
    if db_after_human[key].get("resolution") == "unclear":
        unclear_for_human += 1

solved_by_human = unclear_for_llms - unclear_for_human

secondary_blocks = 2


# Total number of blcoks and total number of records are different things, because "partial" 
# blocks should be counted as 2 blocks


print(f"Total number of blocks: {len(db_pre_human)}")
print(f"-- Number of non-conflictive blocks: {non_conflictive}")
print(f"-- Number of conflictive blocks: {conflictive}")
print(f"    -- Number of blocks solved by LLMs: {solved_by_llms}")
print(f"    -- Number of blocks unclear for LLMs: {unclear_for_llms}")
print(f"         -- Number of blocks solved by human: {solved_by_human}")
print(f"         -- Number of blocks unclear for human: {unclear_for_human}")

