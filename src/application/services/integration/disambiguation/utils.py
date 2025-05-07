from bson import ObjectId


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
                full_publication = publication_dict.get(pub_str_id)
                if full_publication:
                    pubs.append(publication_dict.get(pub_str_id).get('data'))
        
        doc['data']['publication'] = pubs
        doc['_id'] = str(doc['_id'])
        doc_dict[doc['_id']] = doc

    return doc_dict


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
            "publication": entry["data"].get("publication"),
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