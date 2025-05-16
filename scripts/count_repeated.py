
import json

file = 'human_annotations/human_conflicts_log.jsonl'

keys = list()
# read each line 
with open(file, 'r') as f:
    for line in f:
        try:
            record = json.loads(line)
            key = list(record.keys())[0]
            keys.append(key)
        except json.JSONDecodeError:
            continue  # optionally log bad lines

print(f"Number of unique ids in human_conflicts_log.jsonl: {len(keys)}")

counts = dict()
for key in keys:
    if key not in counts:
        counts[key] = 1
    else:
        counts[key] += 1

for key in counts:
    if counts[key] > 1:
        print(f"Key: {key} has {counts[key]} entries")


