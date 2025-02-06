import os
import logging 
from typing import List, Dict
from src.application.services.transformation.standardizers_factory import MetadataStandardizerFactory
from src.application.services.transformation.metadata import create_new_metadata, update_existing_metadata
from src.domain.models.metadata import Metadata
from src.infrastructure.db.mongo_adapter import MongoDBAdapter


ALAMBIQUE = os.getenv('ALAMBIQUE', 'alambiqueDev')
PRETOOLS = os.getenv('PRETOOLS', 'pretoolsDev')

def standardize_entry(identifier: str,  raw: Dict, source: str) -> List[Dict]:
    
    if not identifier:
        logging.debug("No identifier found for entry; skipping...")
        return

    # Standardize the software metadata entries into the standard data model
    standardizer = MetadataStandardizerFactory.get_standardizer(source)
    tools = standardizer.process_transformation(raw)

    # To dictionary 
    tools_dicts = [inst.model_dump() for inst in tools]
    
    return(tools_dicts)


def generate_metadata(raw_entry, identifier):
    """
    Generate or update metadata for a given identifier using a database adapter.

    This function checks if metadata for a given identifier exists in the PRETOOLS collection of a database. If the metadata exists, it is updated using the current metadata; if it does not exist, new metadata is created. The operation uses various helper functions and methods from the DatabaseAdapter to check existence, retrieve existing metadata, and to update or create metadata.

    Args:
        identifier (str): The unique identifier for which metadata is to be generated or updated.

    Returns:
        Metadata: An instance of the Metadata class containing the generated or updated metadata.
    """
    mongo_adapter = MongoDBAdapter()
    entry_exists_db = mongo_adapter.entry_exists(PRETOOLS, identifier)

    if entry_exists_db == False:
        source_url = raw_entry.get('@source_url', None)
        source_identifier = get_identifier(raw_entry)
        metadata = create_new_metadata(source_identifier, source_url, ALAMBIQUE)
    else:
        existing_metadata  = mongo_adapter.get_entry_metadata(PRETOOLS, identifier)
        existing_metadata = Metadata(**existing_metadata)
        metadata = update_existing_metadata(PRETOOLS, existing_metadata)
    
    metadata_dict = metadata.model_dump()

    return metadata_dict



def save_entry(identifier, software_metadata_dict, raw_entry):
    '''
    Save the entry in the database
    '''
    # Generate metadata for the new metada entry
    identifier = f'{software_metadata_dict['source'][0]}/{software_metadata_dict['name']}/{software_metadata_dict['type']}/{software_metadata_dict['version']}'
    entry_metadata = generate_metadata(raw_entry, identifier)

    # Push to the database 
    push_to_db(software_metadata_dict, entry_metadata, identifier)

    return


def push_to_db(software_metadata_dict, entry_metadata, identifier):
    mongo_adapter = MongoDBAdapter()

    try:
        # Build the entry merging entry metadata and content (software metadata)
        document = entry_metadata
        document['data'] = software_metadata_dict

        # Update or insert in database
        if mongo_adapter.entry_exists(PRETOOLS, identifier):
            mongo_adapter.update_entry(PRETOOLS, identifier, document)
        else:
            mongo_adapter.insert_one(PRETOOLS, document)
    
    except Exception as e:
        logging.error(f"An error occurred while processing entry {identifier}: {e}")