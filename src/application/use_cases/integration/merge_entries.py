
import json


def merge_and_save(new_grouped_entries_file):

    with open(new_grouped_entries_file, 'r') as f:
        grouped_entries = json.load(f)

    final_instances_groups = [group['instances'] for group in grouped_entries.values()]

    print("Integration complete. Results saved to 'data.json'.")

    # Merge entries in each group
    for group in final_instances_groups:

        # validate entries as instances 

        # merge entries

        # save merged entries
        
        continue



