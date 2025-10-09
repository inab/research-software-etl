import json
import os
import tempfile

def deduplicate_jsonl_inplace(file_path):
    seen_keys = set()
    
    # create a temporary file in the same directory
    dir_name = os.path.dirname(file_path)
    with tempfile.NamedTemporaryFile(mode="w", dir=dir_name, delete=False, encoding="utf-8") as tmpfile:
        tmp_path = tmpfile.name
        
        with open(file_path, "r", encoding="utf-8") as infile:
            for line in infile:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue  # skip broken lines

                key = next(iter(obj))  # each line has exactly one key
                if key not in seen_keys:
                    seen_keys.add(key)
                    tmpfile.write(json.dumps(obj, ensure_ascii=False) + "\n")
    
    # replace the original file with the deduplicated one
    os.replace(tmp_path, file_path)

# Example usage:
deduplicate_jsonl_inplace("scripts/data/disambiguated_blocks.jsonl")
