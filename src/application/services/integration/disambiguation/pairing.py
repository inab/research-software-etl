import logging
from pprint import pprint
from src.domain.models.software_instance.multitype_instance import multitype_instance


def convert_to_multi_type_instance(instance_data_dict):
    if instance_data_dict['type'] and isinstance(instance_data_dict['type'], str):
        instance_data_dict['type'] = [instance_data_dict['type']]
    elif instance_data_dict['type'] and isinstance(instance_data_dict['type'], list):
        instance_data_dict['type'] = instance_data_dict['type']
    else:
        instance_data_dict['type'] = []
    
    instance_data_dict['other_names'] = []

    #pprint(instance_data_dict)

    return multitype_instance(**instance_data_dict)


def merge_instances(instances):
    merged_instances = instances[0]
    for instance in instances[1:]:
        merged_instances = merged_instances.merge(instance)   

    return merged_instances 

def merge_remaining(entries):
    entries_remaining_dict = {}
    for entry in entries:
        id = entry["_id"]
        metadata = entry["data"]
        entries_remaining_dict[id] = convert_to_multi_type_instance(metadata)
    
    print('Instances in group converted to multitype_instance.')
    ids_remaining = [entry["_id"] for entry in entries]
    # merge entries
    print(f"Merging {len(entries_remaining_dict)} entries in group...")
    instances = [entries_remaining_dict[id] for id in ids_remaining]
    merged_instances = merge_instances(instances)

    # convert to dictionary again
    entry_remaining_merged = merged_instances.model_dump(mode="json")

    return entry_remaining_merged, ids_remaining

def build_pairs(full_conflict, key, more_than_two_pairs):
    """
    Function to build pairs of disconnected and remaining entries.
    It checks the number of entries in each group and handles them accordingly.
    - If there are no disconnected entries, it skips the conflict.
    - If there are more than two disconnected entries, it creates several pairs.
    - If there are more than two remaining entries, it merges them into one entry.
    """
    pairs = []

    disconnected = full_conflict.get("disconnected", [])
    remaining = full_conflict.get("remaining", [])

    if len(disconnected) == 0:
        # No conflict to resolve
        logging.info(f"Conflict {key} has no disconnected entries. Skipping.")
        return pairs, more_than_two_pairs

    elif len(disconnected) > 1:
        more_than_two_pairs += 1

        if len(remaining) == 0:
            if len(disconnected) == 2:
                # Treat first as remaining, second as disconnected
                pair = {
                    "remaining": [disconnected[0]],
                    "disconnected": [disconnected[1]]
                }
                pairs.append(pair)
            else:
                # No remaining, and more than two disconnected – pair disconnected entries among themselves
                for i in range(1, len(disconnected)):
                    pair = {
                        "remaining": [disconnected[0]],  # use first as pseudo-"remaining"
                        "disconnected": disconnected[i]
                    }
                    pairs.append(pair)
            return pairs, more_than_two_pairs

        elif len(remaining) == 1:
            # Pair each disconnected with the single remaining
            for disc in disconnected:
                pair = {
                    "remaining": [remaining[0]],
                    "disconnected": [disc]
                }
                pairs.append(pair)
            return pairs, more_than_two_pairs

        elif len(remaining) > 1:
            # Merge remaining entries into one, and pair each disconnected with the merged remaining
            merged = merge_remaining(remaining)
            for disc in disconnected:
                pair = {
                    "remaining": [merged],
                    "disconnected": [disc]
                }
                pairs.append(pair)
            return pairs, more_than_two_pairs

    else:
        # Only one disconnected entry
        if len(remaining) == 0:
            # Not enough context to make a pair
            logging.info(f"Conflict {key} has only one disconnected and no remaining entries. Skipping.")
            return pairs, more_than_two_pairs

        elif len(remaining) == 1:
            # Simple pair
            pairs.append(full_conflict)
            return pairs, more_than_two_pairs

        elif len(remaining) > 1:
            # Merge remaining entries and create one pair
            merged, merged_ids = merge_remaining(remaining)
            full_conflict['remaining'] = [{"_id": ','.join(merged_ids) ,"data": merged}]
            pairs.append(full_conflict)
            return pairs, more_than_two_pairs

    return pairs, more_than_two_pairs


