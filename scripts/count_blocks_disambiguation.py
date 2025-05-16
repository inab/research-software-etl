from src.application.services.integration.disambiguation.utils import load_dict_from_jsonl

# ----------------------------------------------------
# Count the number of blocks in the disambiguation process
# 
# Warning: will not work anymore because now the decision of issues is 'merged', 
# 'partial' or 'unclear' in disambiguated instead of the decision of 
# literally the human reviewer (which is 'same', 'different', 'unclear')
# ----------------------------------------------------

db_first_path = 'scripts/data/disambiguated_blocks_first_round.jsonl'

db_pre_human_path = 'scripts/data/disambiguated_blocks_second_round.jsonl'
db_after_human_path = 'scripts/data/disambiguated_blocks.jsonl'

db_first = load_dict_from_jsonl(db_first_path)

non_conflictive = 0
conflictive = 0
solved_by_llms = 0
unclear_for_llms = 0
solved_by_human = 0
unclear_for_human = 0



db_pre_human = load_dict_from_jsonl(db_pre_human_path)
for key in db_pre_human:
    if db_pre_human[key].get("resolution") == "no_conflict":
        non_conflictive += 1
    else:
        if '_secondary_' in key:
            # This is a secondary block, so we don't count it
            continue
        conflictive += 1
        if db_pre_human[key].get("resolution") == "manual_review_pending":
            unclear_for_llms += 1
        else:
            solved_by_llms += 1

db_after_human = load_dict_from_jsonl(db_after_human_path)
for key in db_after_human:
    if db_after_human[key].get("resolution") == "unclear":
        unclear_for_human += 1

solved_by_human = unclear_for_llms - unclear_for_human

print(f"Total number of blocks: {len(db_first)}")
print(f"-- Number of non-conflictive blocks: {non_conflictive}")
print(f"-- Number of conflictive blocks: {conflictive}")
print(f"    -- Number of blocks solved by LLMs: {solved_by_llms}")
print(f"    -- Number of blocks unclear for LLMs: {unclear_for_llms}")
print(f"         -- Number of blocks solved by human: {solved_by_human}")
print(f"         -- Number of blocks unclear for human: {unclear_for_human}")

'''
Total number of blocks: 45213
-- Number of non-conflictive blocks: 44685
-- Number of conflictive blocks: 555
    -- Number of blocks solved by LLMs: 440
    -- Number of blocks unclear for LLMs: 115
         -- Number of blocks solved by human: 98
         -- Number of blocks unclear for human: 17
'''