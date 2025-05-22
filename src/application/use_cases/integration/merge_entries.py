
import json
from bson import json_util
from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId
from pydantic.json import pydantic_encoder
from src.domain.models.software_instance.main import instance
from src.domain.models.software_instance.multitype_instance import multitype_instance
from src.application.services.integration.disambiguation.utils import load_dict_from_jsonl
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
        

def fetch_entry_from_db(entry_id):
    query = {
        "_id": entry_id
    }
    entry = mongo_adapter.fetch_entry(
        collection_name='pretoolsDev',
        query=query
    ) 
    if entry:
        return entry
    else:
        return None





def prepare_for_db(entry, entries_ids):
    """
    WARNING: this function inserts the entries in the db even if the entry is already there.
    This is because it is for the first time we are merging the entries.

    TODO: adapt this function to check if the entry is already in the db and if so,
    update it instead of inserting it again. Add metadata to reflect updates in it. 
    """
    # make suere entries_ids is a list
    if not isinstance(entries_ids, list):
        entries_ids = [entries_ids]
    
    db_entry = {
        'source': entries_ids,
        "timestamp": datetime.now().isoformat()
    }

    db_entry['data'] = entry

    return db_entry


def merge_entries(entries_ids):
    # retrieve full entries from db
    entries = [fetch_entry_from_db(entry) for entry in entries_ids]
    # Put type in list and validate entries as multitype_instance
    instances = [convert_to_multi_type_instance(entry) for entry in entries]
    print('Instances in entries_ids converted to multitype_instance.')

    # merge entries
    if len(instances) > 1:
        # merge instances
        print(f"Merging {len(instances)} entries in entries_ids...")
        merged_instances = merge_instances(instances)
        print('Entries in entries_ids merged.')
    else:
        merged_instances = instances[0]
        print(f"Only one entry in entries_ids. No merging needed.")

    merged_entries = merged_instances.model_dump(mode="json")   

    return merged_entries


def save_entry(metadata):
    try:
        id = mongo_adapter.insert_one(
            collection_name='toolsDev',
            document=metadata
        )

    except Exception as e:
        print(f"Error saving entry {metadata['_id']}.")
        pretty_print_model(metadata)
        raise

    else:
        return id
    

def merge_and_save_blocks(disambiguated_blocks_file):
    '''
    Merge entries if:
        - resolution == merged or resolution == no_conflict:
            - merge “merged entries”
        - resolution == partial:
            - merge “merged entries”
            - save entry in “unmerge_entry” if len == 1
    '''

    disambiguated_blocks = load_dict_from_jsonl(disambiguated_blocks_file)
    print('Disambiguated blocks loaded.')

    summary = {
        "N": len(disambiguated_blocks),
        "n_processed": 0,
        "n_inserted_entries": 0,
        "n_pending": 0,
        "n_unclear": 0
    }

    for key, value in disambiguated_blocks.items():
        try:
            if value.get("resolution") == "no_conflict" or value.get("resolution") == "merged":
                entry = merge_entries(value.get("merged_entries"))
                db_entry = prepare_for_db(entry, value.get("merged_entries"))
                db_id = save_entry(db_entry)
                print(f"Entry {key} saved in db with id {db_id}.")
                summary['n_processed'] += 1
                summary['n_inserted_entries'] += 1

            elif value.get("resolution") == "partial":
                entry = merge_entries(value.get("merged_entries"))
                db_entry = prepare_for_db(entry, value.get("merged_entries"))
                db_id = save_entry(db_entry)
                print(f"Entry {key} saved in db with id {db_id}.")
                summary['n_inserted_entries'] += 1

                if len(value.get("unmerged_entries"))==1:
                    entry = merge_entries(value.get("unmerged_entries"))
                    db_entry = prepare_for_db(entry, value.get("unmerged_entries"))
                    db_id = save_entry(db_entry)
                    print(f"Entry {key} saved in db with id {db_id}.")
                    summary['n_inserted_entries'] += 1
                
                summary['n_processed'] += 1
            
            else:
                if value.get("resolution") == "unclear":
                    summary['n_unclear'] += 1
                elif value.get("resolution") == "manual_review_pending":
                    summary['n_pending'] += 1
            
        except:
            print(f"Error processing block {key}.")
            raise

    return summary





if __name__ == '__main__':
    file_path = '/Users/evabsc/projects/software-observatory/research-software-etl/scripts/data/grouped_entries.json'
    merge_and_save_blocks(file_path)