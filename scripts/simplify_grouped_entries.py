import json 

with open('scripts/data/grouped_entries_no_opeb.json', 'r') as f:
    blocks = json.load(f)

for block in blocks.values():
    block["instances"] = [instance["_id"] for instance in block["instances"]]

with open('scripts/data/blocks.json', 'w') as f:
    json.dump(blocks, f, indent=2)

print("Grouped entries simplified and saved to 'blocks.json'.")
