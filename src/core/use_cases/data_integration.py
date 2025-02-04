import json
import os
from typing import List, Dict
from collections import defaultdict

from src.infrastructure.db.mongo_adapter import MongoDBAdapter
from src.adapters.db.database_adapter import DatabaseAdapter
from src.core.domain.entities.software_instance.main import instance
from src.core.domain.services.integration.metadata import create_new_metadata, update_existing_metadata
db_adapter = MongoDBAdapter()

# collections 
PRETOOLS = os.getenv('PRETOOLS', 'pretoolsDev')
TOOLS = os.getenv('TOOLS', 'toolsDev')
HISTORICAL_TOOLS = os.getenv('HISTORICAL_TOOLS', 'historical_toolsDev')

def should_update(new_data, existing_data):
    # Simple comparison logic; this should be expanded based on actual schema and requirements
    return json.dumps(new_data, sort_keys=True) != json.dumps(existing_data, sort_keys=True)

def fetch_current_document(name, type):
    query = {"data.name": name, "data.type": type}
    current_document = db_adapter.fetch_entry(TOOLS, query)
    return current_document

def move_to_historical(document: Dict):
    db_adapter.insert_one(HISTORICAL_TOOLS, document)
    return

def update_primary_tools_colletion(document: Dict, metadata: Dict):
    db_adapter = MongoDBAdapter()
    doc = metadata.to_dict_for_db_insertion()
    doc['data'] = document
    db_adapter.update_entry(TOOLS, doc)
    return

def insert_into_primary_tools_collection(document: Dict, metadata: Dict):
    db_adapter = MongoDBAdapter()
    doc = metadata.to_dict_for_db_insertion()
    doc['data'] = document
    db_adapter.insert_one(TOOLS, document)
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


def process_groups(grouped_instances):
    """
    Pocesses groups of instances that have the same name and type.
    Args:
        grouped_instances (Dict): Dictionary where keys are tuples of (name, type) and values are lists of instances with that key.
    """
    for key, instances in grouped_instances.items():
        # Integration 
        merged_instance = merge_instances(instances)
        # Save to database  
        source_identifiers = [inst.source_identifier for inst in instances]
        merged_instance_to_database(merged_instance, source_identifiers)
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


def extract_links(instances):
    '''
    IN: {
    'name/type': [instance1, instance2, ...],
    'name/type': [instance3, instance4, ...],
    }
    OUT: {
    'name/type': [link1, link2, ...],
    'name/type': [link3, link4, ...],
    }
    '''
    pass

def group_by_links(instances):
    main_sources = ['biotools','galaxy','galaxy_metadata', 'toolshed', 'bioconda', 'bioconda_recipes' ]
    repository_sources = ['github', 'sourceforge', 'bioconductor']

    # Step 1: Generate Set A: Make name and type groups with instances from main_sources.
    instances_set_a = [inst for inst in instances if inst.source[0] in main_sources]
    grouped_instances_set_a = group_by_key(instances_set_a)
    
    # Step 2: Extract github, sourceforge and bioconductor links from instances in Set A. 
    set_a_w_links = extract_links(grouped_instances_set_a)
    all_links_a = [link for links in set_a_w_links.values() for link in links] 

    # Step 3: Generate Set B: Group by name-type instances from repository_sources that are not in Set B.
    ## Keep the URL of instances in B.
    instances_set_b = [inst for inst in instances if inst.source[0] in repository_sources]
    instances_set_b = [inst for inst in instances_set_b if inst.source_url not in all_links_a]
    grouped_instances_set_b = group_by_key(instances_set_b)

    # Step 4: Extract github, sourceforge and bioconductor links from instances in Set B.
    set_b_w_links = extract_links(grouped_instances_set_b)
    all_links_b = [link for links in set_b_w_links.values() for link in links]

    # Step 5: Remove tools in Set B whose link is in other tool of Set B.
    instances_set_b = [inst for inst in instances_set_b if inst.source_url not in all_links_b]

    # Step 6: Merge instances in Set A and Set B.

    # Step 7: Make groups by name and type. If there are different github, etc links for same name and type, notify about it.

def full_merge_process(instances: List, batch_size: int = 100):
    """
    Group metadata objects by key, process each group in batches, and merge instances within each batch.
    This ensured that all documents describing the same software are processed together.
    Args:
        metadata_objects (List[Metadata]): List of metadata objects to be merged.
        batch_size (int): Number of instances to process in each batch.
    """
    grouped_instances = group_by_key(instances)
    return process_groups(grouped_instances, batch_size)


def fetch_pretools():
    """
    Get all entries from the pretools collection.
    Returns a list of dictionaries with the data field of each entry.
    """
    db_adapter = MongoDBAdapter()
    query = {}
    db_collection = PRETOOLS

    documents = db_adapter.fetch_entries(db_collection, query)
    validated_documents = db_adapter.validate_pretools_data(documents)
    
    return [doc['data'] for doc in validated_documents]



# Example usage
def integration_process():
    instances = fetch_pretools()
    final_merged_data = full_merge_process(instances, batch_size=100)
    return final_merged_data
