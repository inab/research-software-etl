import json
import os
import logging
from typing import List, Dict
from collections import defaultdict

from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from src.infrastructure.db.mongo.standardized_software_repository import StdSoftwareMetaRepository
from src.domain.models.software_instance.main import instance

logger = logging.getLogger("rs-etl-pipeline")


# collections 
PRETOOLS = os.getenv('PRETOOLS', 'pretoolsDev')
TOOLS = os.getenv('TOOLS', 'toolsDev')
HISTORICAL_TOOLS = os.getenv('HISTORICAL_TOOLS', 'historical_toolsDev')

def should_update(new_data, existing_data):
    # Simple comparison logic; this should be expanded based on actual schema and requirements
    return json.dumps(new_data, sort_keys=True) != json.dumps(existing_data, sort_keys=True)

def fetch_current_document(name, type):
    query = {"data.name": name, "data.type": type}
    current_document = mongo_adapter.fetch_entry(TOOLS, query)
    return current_document

def move_to_historical(document: Dict):
    mongo_adapter.insert_one(HISTORICAL_TOOLS, document)
    return

def update_primary_tools_colletion(document: Dict, metadata: Dict):
    doc = metadata.to_dict_for_db_insertion()
    doc['data'] = document
    mongo_adapter.update_entry(TOOLS, doc)
    return

def insert_into_primary_tools_collection(document: Dict, metadata: Dict):
    doc = metadata.to_dict_for_db_insertion()
    doc['data'] = document
    mongo_adapter.insert_one(TOOLS, document)
    return

def merged_instance_to_database(instance, source_identifiers):
    # Fetch the current document
    current_document = fetch_current_document(instance.name, instance.type)
    
    # Check if update is necessary
    if should_update(instance.__dict__, current_document['data']):
        metadata = update_existing_metadata(instance.name, instance.type, source_identifiers)
        move_to_historical(current_document)
        update_primary_tools_colletion(instance, metadata)
        
        pass
    else:
        if not current_document:
            # Generate metadata
            metadata = create_new_metadata(instance.name, instance.type)
            # Insert new document in primary collection        
    pass





def process_groups(grouped_entries):
    """
    Pocesses groups of instances that have the same name and type.
    Args:
        grouped_instances (Dict): Dictionary where keys are tuples of (name, type) and values are lists of instances with that key.
    """
    logger.info('Processing groups')
    logger.info(grouped_entries)
    for entries_group in grouped_entries:
        
        logger.info(entries_group)
        logger.info('-------------------')
        # Turn entries into instancies
        instances = [instance(**entry) for entry in entries_group]
        # Integration 
        merged_instance = merge_instances(instances)
        # Save to database  
        # source_identifiers = [inst.source_identifier for inst in instances]
        # merged_instance_to_database(merged_instance, source_identifiers)

        merged_instance_dict = merged_instance.model_dump_json()
        
        
        print(merged_instance_dict)
        print('-------------------')
        print('-------------------')

    return

def merge_instances(instances):
    """
    For a group of instance of same type and name, merge them into a single instance.
    Args:
        instances (List): List of instance objects.
    Returns:
        Instance: A single instance object that is the result of merging all instances in the input list.
    """
    merged_instance = instances[0]
    
    for inst in instances[1:]:
        merged_instance = merged_instance.merge(inst)
    
    return merged_instance


def group_by_key(instances):
    """
    Given a list of instances, group them by a key that is a tuple of the instance name and type.
    Args:
        instances (List): List of instance objects.
    
    Returns:
        Dict: A dictionary where keys are tuples of (name, type) and values are lists of instances with that key.
    
    """
    grouped_instances = defaultdict(list)
    for inst in instances:
        key = (inst.name.lower(), inst.type)  # Grouping key
        grouped_instances[key].append(inst)
    return grouped_instances


def group_by_link(set_a, set_b):
    """
    Group instances by links.
        """
    logger.info(f"grouping by link: {len(set_a)} and {len(set_b)}")
    # Iterate through each entry in set_b
    for value_b in list(set_b):  # Use list() to safely modify set_b while iterating
        #print(value_b)
        for value_a in set_a:
            #print(value_a)
            # Check if there is a shared link between value_a and value_b
            if any(link in value_a['links'] for link in value_b['links']):
                # Merge instances
                value_a['instances'].extend(value_b['instances'])
                
                # Merge unique links
                value_a['links'] = list(set(value_a['links']) | set(value_b['links']))
                
                # Remove from set_b
                set_b.remove(value_b)
                
                # Stop checking other elements in set_a, as this entry from set_b is already merged
                break

    return set_a, set_b

        
def extract_links(instances):
    '''
    For a list of instances, extract links in repository and webpage.
    '''
    links = []
    for instance in instances:
        # add repos
        for repo in instance['repository']:
            if repo.get('url'):
                links.append(repo['url'])
        
        # add webpage
        if instance.get('webpage'):
            for link in instance['webpage']:
                links.append(link)

    return links
    

def extract_source_url(entries):
    '''
    Extract source url from entries. 
    '''
    # Extract source url from entries
    links = []
    for entry in entries:
        # add source url
        links.append(entry['source_url'])

    return links

def build_structured_set_all_links(entries_lists):
   
    structured_set = []
    for entry_list in entries_lists:
        new_item = {
            'instances': entry_list,
            'links': extract_links(entry_list)
        }
        structured_set.append(new_item)
    
    return structured_set

def build_structured_set_source_url(entries_lists):
    structured_set = []
    for entry_list in entries_lists:
        new_item = {
            'instances': entry_list,
            'links': extract_source_url(entry_list)
        }
        structured_set.append(new_item)
    
    return structured_set


def group_data_entries(data_entries):
    main_sources = ['biotools','galaxy','galaxy_metadata', 'toolshed', 'bioconda', 'bioconda_recipes' ]
    repository_sources = ['github', 'sourceforge', 'bioconductor']

    # Generate Sets A and B
    data_entries_set_a = [data_entry for data_entry in data_entries if data_entry['source'][0] in main_sources]
    data_entries_set_b = [data_entry for data_entry in data_entries if data_entry['source'][0] in repository_sources]

    # Group by key in set A
    grouped_set_a = [ value for key,value in group_by_key(data_entries_set_a).items()]

    # Group by link inside set B. Merge tools in Set B whose link is in other tool of Set B.
    grouped_set_b = [[inst] for inst in data_entries_set_b] # in this set each instance is a group by itself
    structured_set_b = build_structured_set_source_url(grouped_set_b)
    structured_set_b_entriched, structured_set_b_remining = group_by_link(structured_set_b, structured_set_b) 
    structured_set_b = structured_set_b_entriched + structured_set_b_remining

    # Group by link Set A and Set B. Merge tools in Set B whose link is in other tool of Set A.
    structured_set_a = build_structured_set_all_links(grouped_set_a)
    set_a, set_b = group_by_link(structured_set_a, structured_set_b)

    # Group Set B: Make name and type groups with instances from repository_sources.
    #remaining_data_entries_set_b = []
    #for dict in set_b:
    #    remaining_data_entries_set_b.extend(dict['instances'])
    
    #grouped_remaining_set_b = group_by_key(remaining_data_entries_set_b)
    #data_entries_b = [ value for key,value in grouped_remaining_set_b.items()]

    # Merge entries in Set A and Set B.
    #data_entries_a = []
    #for dict in set_a:
    #    data_entries_a.append(dict['instances'])

    all_grouped_data_entries = set_a + set_b

    logger.info('Grouped data entries')
    logger.info(all_grouped_data_entries)

    # NOT YET: Step 7: Make groups by name and type. If there are different github, etc links for same name and type, notify about it.
    return all_grouped_data_entries


def full_merge_process(entries: List):
    """

    """
    grouped_entries = group_data_entries(entries)
    return process_groups(grouped_entries)


def fetch_pretools():
    """
    Get all entries from the pretools collection.
    Returns a list of dictionaries with the data field of each entry.
    """
    std_software_repo = StdSoftwareMetaRepository(mongo_adapter)

    # fetch entries 
    # IGNORE OPEB_METRICS and BIOCONDA (OPEB_TOOLS_BIOCONDA)
    raw_entries = std_software_repo.get_standardized_software_data()

    # validated_documents = mongo_adapter.validate_pretools_data(documents) # do not validate for now
    entries = []
    
    for entry in raw_entries:
        if entries == 100:
            return entries
        #print(entry)
        entry['data']['source_url'] = entry['source'][0]['source_url']
        entries.append(entry['data'])

    return entries



# Example usage
def integration_process():
    entries = fetch_pretools()
    logger.info('Starting integration process')
    final_merged_data = full_merge_process(entries[:100])
    return final_merged_data
