from bson import ObjectId
import json
import os

def build_instances_keys_dict():
    from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter

    # Step 1: Build a publication lookup dict with stringified ObjectIds
    publication_dict = {
        str(doc['_id']): {**doc, "_id": str(doc['_id'])}
        for doc in mongo_adapter.fetch_entries( "publicationsMetadataDev", {})
    }
    # Step 2: Build the main document dictionary and replace data.publication
    doc_dict = {}
    for doc in mongo_adapter.fetch_entries( "pretoolsDev", {}):
        pub_ids= doc.get('data', {}).get('publication')
        pubs = []
        for pub_id in pub_ids:
            if isinstance(pub_id, ObjectId):
                pub_str_id = str(pub_id)
                pubs.append(pub_str_id)
        
        doc['data']['publication'] = pubs
        doc['_id'] = str(doc['_id'])

        doc_dict[doc['_id']] = doc

    return doc_dict


def get_pub(object_id):
    from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter

    publication = mongo_adapter.fetch_entry( "publicationsMetadataDev", object_id)
    # Step 2: Build the main document dictionary and replace data.publication
    
    if publication:
        return publication.get('data')
    else:
        return None

def load_dict_from_jsonl(path):
    result = {}
    with open(path, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)
                if not isinstance(entry, dict):
                    raise ValueError("Each line must be a dictionary")
                result.update(entry)
            except json.JSONDecodeError as e:
                print(f"Skipping invalid line: {e}")
    return result


def update_jsonl_record(path, new_record):
    updated_key = next(iter(new_record))  # Assumes one key per record
    updated = False
    temp_path = path + '.tmp'

    with open(path, 'r') as infile, open(temp_path, 'w') as outfile:
        for line in infile:
            try:
                record = json.loads(line)
                key = next(iter(record))
                if key == updated_key:
                    json.dump(new_record, outfile)
                    updated = True
                else:
                    json.dump(record, outfile)
                outfile.write('\n')
            except json.JSONDecodeError:
                continue  # optionally log bad lines

    if not updated:
        # Append the new record if it wasn't found
        with open(temp_path, 'a') as outfile:
            json.dump(new_record, outfile)
            outfile.write('\n')

    os.replace(temp_path, path)  # atomic rename

def add_jsonl_record(path, new_record):
    with open(path, 'a') as f:
            json.dump(new_record, f)
            f.write('\n')


def process_publications(publications):
    """
    Process the publications in the entries and replace
    the publication IDs with the corresponding publication data.
    """
    if not publications:
        return []
    else:
        processed_publications = []
        for publication in publications:
            if isinstance(publication, ObjectId):
                publication_str = str(publication)
                processed_publications.append(get_pub(publication_str))
            else:
                processed_publications.append(publication)
        return processed_publications


def replace_with_full_entries(conflict, instances_dict):
    new_conflict = {
        "disconnected": [],
        "remaining": [],
    }
    for entry in conflict['disconnected']:
        entry_id = entry["id"]
        new_conflict['disconnected'].append(instances_dict.get(entry_id))

    
    for entry in conflict['remaining']:
        entry_id = entry["id"]
        new_conflict['remaining'].append(instances_dict.get(entry_id))

    return new_conflict



def filter_relevant_fields(conflict):
    """
    Filter the relevant fields from the conflict dictionary.
    """
    filtered_conflict = {
        "disconnected": [],
        "remaining": []
    }

    for entry in conflict["disconnected"]:
        filtered_entry = {
            "id": entry["_id"],
            "name": entry["data"].get("name"),
            "description": entry["data"].get("description"),
            "repository": entry["data"].get("repository"),
            "webpage": entry["data"].get("webpage"),
            "source": entry["data"].get("source"),
            "license": entry["data"].get("license"),
            "authors": entry["data"].get("authors"),
            "publication": process_publications(entry["data"].get("publication")),
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