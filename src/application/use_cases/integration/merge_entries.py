
import json
from bson import json_util
from pydantic import BaseModel
from pydantic.json import pydantic_encoder
from src.domain.models.software_instance.main import instance
from src.domain.models.software_instance.multitype_instance import multitype_instance
from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter

def pretty_print_model(model: BaseModel) -> None:
    print(model.model_dump_json(indent=4))


def pretty_print_dict(d):
    print(json.dumps(d, indent=4, sort_keys=True))


def convert_to_multi_type_instance(entry):
    instance_data_dict = entry['data']
    if instance_data_dict['type']:
        instance_data_dict['type'] = [instance_data_dict['type']]
    else:
        instance_data_dict['type'] = []
    
    instance_data_dict['other_names'] = []

    return multitype_instance(**instance_data_dict)


def merge_instances(instances):
    merged_instances = instances[0]
    for instance in instances[1:]:
        merged_instances = merged_instances.merge(instance)   

    return merged_instances 
        


def merge_and_save(disambiguated_blocks_file, instances_dict):

    with open(disambiguated_blocks_file, 'r') as f:
        disambiguated_blocks = f.read()


    print('Grouped entries loaded.')

    # loop disambiguated blocks and merge the entries in 'merged_entries'
    final_instances_groups = []
    for key, value in disambiguated_blocks.items():
        instances_ids = value.get("merged_entries", [])
        if len(value.get('unmerged_entries')) < 1:
            instances_ids += value.get('unmerged_entries')
        else:
            print(f"Group {key} has only one instance. Skipping.")
        final_instances_groups.append(instances_ids)
    
    print('Final instances groups loaded.')

    # Merge entries in each group
    print('-----------------------------------')
    print("Merging process starting. Group by group.")
    count = 0
    for group in final_instances_groups:

        count += 1
        print(f"Group {count}:")
        print('-----------------------------------')

        try:
            # retrieve full entries from instances_dict or db
            instances = [instances_dict.get(entry) for entry in group]
            instances = [item['data'] for item in instances if item is not None]

            # Put type in list and validate entries as multitype_instance
            instances = [convert_to_multi_type_instance(entry) for entry in group]
            print('Instances in group converted to multitype_instance.')

            # merge entries
            print(f"Merging {len(instances)} entries in group...")
            merged_instances = merge_instances(instances)

            print('Entries in group merged.')

            metadata = {
                'source': group,
                'timestamp': '2025-04-28T15:00:00.000Z',
            }

            metadata['data'] = merged_instances.model_dump(mode="json")            

            # save merged entries
            mongo_adapter.insert_one(
                collection_name='toolsDev',
                document=metadata
            )
            # print for now for debugging
        except Exception as e:
            print(f"Error merging group {count}.")            
            pretty_print_dict(group)
            raise

        print('-----------------------------------')


    print("Integration complete.")



if __name__ == '__main__':
    file_path = '/Users/evabsc/projects/software-observatory/research-software-etl/scripts/data/grouped_entries.json'
    merge_and_save(file_path)