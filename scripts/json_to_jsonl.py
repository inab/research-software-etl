import json
import sys

def json_to_jsonl(json_path, jsonl_path):
    with open(json_path, 'r') as infile:
        data = json.load(infile)

    if not isinstance(data, dict):
        raise ValueError("Top-level JSON must be a dictionary.")

    with open(jsonl_path, 'w') as outfile:
        for key, value in data.items():
            json.dump({key: value}, outfile)
            outfile.write('\n')

if __name__ == "__main__":
    files = [
    'tests/application/use_cases/integration/data/blocks.json',
    'tests/application/use_cases/integration/data/conflict_blocks.json',
    #'tests/application/use_cases/integration/data/disambiguated_blocks.json',
    #'scripts/data/blocks.json',
    #'scripts/data/conflict_blocks.json',
    #'scripts/data/disambiguated_blocks.json'
    ]
    
    for file in files:
        output_file = file.replace('.json', '.jsonl')
        json_to_jsonl(file, output_file)
        print(f"Converted {file} to {output_file}")
    