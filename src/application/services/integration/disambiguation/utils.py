import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

def append_dict_to_jsonl(path, data: dict) -> None:
    """
    Appends a dictionary as a single JSON line to a .jsonl file.
    Creates the file and parent directories if they don't exist.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
        f.write("\n")
                
def extract_ids(obj):
    all_ids = []
    for record in obj['remaining']:
        id = record['_id'].split(',')
        for i in id:
            all_ids.append(i)

    for record in obj['disconnected']:
        id = record['_id'].split(',')
        for i in id:
            all_ids.append(i)

    all_ids.sort()
    final_id = ','.join(all_ids)

    return final_id

    
def stable_hash(obj: Any) -> str:
    # actually, it is not a hash anymore
    stable_id = extract_ids(obj)
    return stable_id


def get_pub(object_id, publications):
    publication = publications.get_by_id(object_id)

    if publication:
        return publication.get('data')
    else:
        return None

def load_dict_from_jsonl(path):
    path = Path(path)
    result = {}

    # Create the file if it does not exist
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return result

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if not isinstance(entry, dict):
                    raise ValueError("Each line must be a dictionary")
                result.update(entry)
            except json.JSONDecodeError as e:
                print(f"Skipping invalid line: {e}")

    return result


def remove_jsonl_record(path, target_key):
    #print(f'Removing record(s) with key: {target_key}')
    path = Path(path)
    temp_path = path.with_name(path.name + '.tmp')
    removed = False

    with open(path, 'r') as infile, open(temp_path, 'w') as outfile:
        for line in infile:
            try:
                record = json.loads(line)
                key = next(iter(record))
                if key != target_key:
                    json.dump(record, outfile)
                    outfile.write('\n')
                else:
                    removed = True
            except json.JSONDecodeError:
                continue  # optionally log or keep corrupted lines

    if removed:
        os.replace(temp_path, path)
    else:
        os.remove(temp_path)
        print(f'Key {target_key} not found.')


def update_jsonl_record(path, updated_key, new_value):
    #print(f'Updating record with key: {updated_key}')
    path = Path(path)
    updated = False
    temp_path = path.with_name(path.name + '.tmp')

    with open(path, 'r') as infile, open(temp_path, 'w') as outfile:
        for line in infile:
            try:
                record = json.loads(line)
                key = next(iter(record))
                if key == updated_key:
                    json.dump({updated_key: new_value}, outfile)
                    updated = True
                else:
                    json.dump(record, outfile)
                outfile.write('\n')
            except json.JSONDecodeError:
                continue  # optionally log bad lines

    if not updated:
        with open(temp_path, 'a') as outfile:
            json.dump({updated_key: new_value}, outfile)
            outfile.write('\n')

    os.replace(temp_path, path)  # atomic rename

def add_jsonl_record(path, new_record):
    with open(path, 'a') as f:
            json.dump(new_record, f)
            f.write('\n')


def process_publications(publications, publications_repo):
    """
    Process the publications in the entries and replace
    the publication IDs with the corresponding publication data.
    """
    if not publications:
        return []
    else:
        processed_publications = []
        for publication in publications:
            if isinstance(publication, dict):
                # already a resolved publication object, keep as-is
                processed_publications.append(publication)
            else:
                # an id reference (str, or a stray ObjectId) — resolve it
                processed_publications.append(get_pub(str(publication), publications_repo))
        return processed_publications


def replace_with_full_entries(conflict, pretools):
    """
    Hydrate a conflict's entry ids into full pretools documents.

    NB: this fetches each entry individually. A previous design pre-loaded the
    whole pretools collection into a dict and passed it in, but the dict was
    never read -- the parameter was dead and the full-collection scan was pure
    waste, so both were removed.
    """
    new_conflict = {
        "disconnected": [],
        "remaining": [],
    }
    for entry in conflict['disconnected']:
        new_conflict['disconnected'].append(pretools.get_by_id(entry["id"]))

    for entry in conflict['remaining']:
        new_conflict['remaining'].append(pretools.get_by_id(entry["id"]))

    return new_conflict



def filter_relevant_fields(conflict, publications):
    """
    Filter the relevant fields from the conflict dictionary.
    """
    filtered_conflict = {
        "disconnected": [],
        "remaining": []
    }

    for entry in conflict["disconnected"]:
        #print('Entry:', entry)
        filtered_entry = {
            "id": entry["_id"],
            "name": entry["data"].get("name"),
            "description": entry["data"].get("description"),
            "repository": entry["data"].get("repository"),
            "webpage": entry["data"].get("webpage"),
            "source": entry["data"].get("source"),
            "license": entry["data"].get("license"),
            "authors": entry["data"].get("authors"),
            "publication": process_publications(entry["data"].get("publication"), publications),
            "documentation": entry["data"].get("documentation")
        }
        filtered_conflict["disconnected"].append(filtered_entry)

    for entry in conflict["remaining"]:
        #print('Entry:', entry)
        filtered_entry = {
            "id": entry["_id"],
            "name": entry["data"].get("name"),
            "description": entry["data"].get("description"),
            "repository": entry["data"].get("repository"),
            "webpage": entry["data"].get("webpage"),
            "source": entry["data"].get("source"),
            "license": entry["data"].get("license"),
            "authors": entry["data"].get("authors"),
            "publication": entry["data"].get("publication"),
            "documentation": entry["data"].get("documentation")
        }
        filtered_conflict["remaining"].append(filtered_entry)

    return filtered_conflict



SOURCE_PRIORITY = {
    "human": 2,
    "llm": 1,
}

def parse_ts(ts: str) -> float:
    """Parse ISO timestamp to sortable float."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()

def is_better(new, old):
    """Return True if `new` decision should replace `old`.
       For now, there should be no conflicts solvd by humans and LLMs, but it may be the case in the future
    """
    # 1. Source priority
    if SOURCE_PRIORITY[new["source"]] != SOURCE_PRIORITY[old["source"]]:
        return SOURCE_PRIORITY[new["source"]] > SOURCE_PRIORITY[old["source"]]

    # 2. Confidence (only meaningful for LLM)
    if new.get("confidence", 0) != old.get("confidence", 0):
        return new.get("confidence", 0) > old.get("confidence", 0)

    # 3. Recency
    return parse_ts(new["ts"]) > parse_ts(old["ts"])

def load_pair_decisions(path: str | Path):
    """
    Load pair decisions from JSONL and return best decision per pair_key.
    """
    best_pair = {}

    path = Path(path)
    if not path.exists():
        return best_pair  # empty cache is fine

    with path.open() as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("kind") != "pair":
                continue

            key = row["pair_id"]
            if key not in best_pair:
                best_pair[key] = row
            else:
                if is_better(row, best_pair[key]):
                    best_pair[key] = row

    return best_pair