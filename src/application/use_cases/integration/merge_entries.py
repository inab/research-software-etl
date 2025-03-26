
import json
from bson import json_util
from pydantic import BaseModel
from pydantic.json import pydantic_encoder
from src.domain.models.software_instance.main import instance
from src.domain.models.software_instance.multitype_instance import multitype_instance

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
        


def merge_and_save(new_grouped_entries_file):

    with open(new_grouped_entries_file, 'r') as f:
        file_contents = f.read()

    grouped_entries = json_util.loads(file_contents)

    print('Grouped entries loaded.')

    final_instances_groups = [group['instances'] for group in grouped_entries.values()]
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
            # Put type in list and validate entries as multitype_instance
            instances = [convert_to_multi_type_instance(entry) for entry in group]
            print('Instances in group converted to multitype_instance.')

            # merge entries
            print(f"Merging {len(instances)} entries in group...")
            merged_instances = merge_instances(instances)
            
            
            print('Entries in group merged.')

            # save merged entries
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