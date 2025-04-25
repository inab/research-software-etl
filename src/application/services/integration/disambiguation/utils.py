
def build_instances_keys_dict(data):
    """Create a mapping of instance IDs to their respective instance data."""
    instances_keys = {}
    for key, value in data.items():
        instances = value.get("instances", [])
        for instance in instances:
            instances_keys[instance["_id"]] = instance
    return instances_keys


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
            "id": entry["id"],
            "name": entry["name"],
            "description": entry["description"],
            "repository": entry["repository"],
            "webpage": entry["webpage"],
            "source": entry["source"],
            "license": entry["license"],
            "authors": entry["authors"],
            "publication": entry["publication"],
            "documentation": entry["documentation"],
        }
        filtered_conflict["disconnected"].append(filtered_entry)

    for entry in conflict["remaining"]:
        filtered_entry = {
            "id": entry["id"],
            "name": entry["name"],
            "description": entry["description"],
            "repository": entry["repository"],
            "webpage": entry["webpage"],
            "source": entry["source"],
            "license": entry["license"],
            "authors": entry["authors"],
            "publication": entry["publication"],
            "documentation": entry["documentation"],
        }
        filtered_conflict["remaining"].append(filtered_entry)

    return filtered_conflict