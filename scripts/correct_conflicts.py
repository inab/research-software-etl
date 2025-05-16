from src.application.services.integration.disambiguation.utils import remove_jsonl_record, load_dict_from_jsonl, add_jsonl_record, update_jsonl_record
import json 

correct_records_path = 'scripts/data/final_corrected_conflict_blocks_2.jsonl'
conflict_blocks_path = 'scripts/data/conflict_blocks.jsonl'
disambiguated_blocks_path = 'scripts/data/disambiguated_blocks.jsonl'

correct_records = load_dict_from_jsonl(correct_records_path)
conflict_blocks = load_dict_from_jsonl(conflict_blocks_path)

'''
for key in correct_records:
    print('Key:', key)
    update_jsonl_record(conflict_blocks_path, key, correct_records[key])


# remove lines from conflict_blocks.jsonl that are in final_corrected_conflict_blocks.jsonl
for key in correct_records:
    print('Key:', key)
    remove_jsonl_record(disambiguated_blocks_path, key)
    # remove_jsonl_record(disambiguated_blocks_path, key)
    # update_jsonl_record(disambiguated_blocks_path, key, correct_records[key])
    # add_jsonl_record(disambiguated_blocks_path, correct_records[key])

'''

# Count unique ids in proxy_results 

proxy_results_path = 'scripts/data/results_proxy.jsonl'

with open(proxy_results_path, 'r') as f:
    unique_ids = set()
    for line in f:
        try:
            record = json.loads(line)
            key = list(record.keys())[0]
            if 'secondary_' in key:
                continue
            unique_ids.add(key)
        except json.JSONDecodeError:
            continue  # optionally log bad lines

    print(f"Number of unique ids in proxy_results.jsonl: {len(unique_ids)}")

not_processed = []
n = 0
for key in conflict_blocks:
    if 'secondary_' in key:
        continue
    n += 1
    if key not in unique_ids:
        not_processed.append(key)



print(f"Number of unique ids in conflict_blocks.jsonl: {len(not_processed)}")
print(not_processed)
