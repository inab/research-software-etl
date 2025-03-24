
import json 
from src.application.services.integration.disambiguation import disambiguate_disconnected_entries


def build_instances_keys_dict(data):
    """Create a mapping of instance IDs to their respective instance data."""
    instances_keys = {}
    for key, value in data.items():
        instances = value.get("instances", [])
        for instance in instances:
            instances_keys[instance["_id"]] = instance
    return instances_keys

def disambiguate_entries(grouped_entries_file, 
                         disconnected_entries_file, 
                         new_grouped_entries_file, 
                         results_file):

    with open(grouped_entries_file, 'r') as f:
        grouped_entries = json.load(f)

    instances_dictionary = build_instances_keys_dict(grouped_entries)

    with open(disconnected_entries_file, 'r') as f:
        disconnected_entries = json.load(f)

    disambiguated_grouped = disambiguate_disconnected_entries(disconnected_entries, 
                                                 instances_dictionary, 
                                                 grouped_entries, 
                                                 results_file)

    with open(new_grouped_entries_file, 'w') as f:
        f.write(json.dumps(disambiguated_grouped))

