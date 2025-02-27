import os
import logging 
from typing import List, Dict
from src.application.services.transformation.standardizers_factory import MetadataStandardizerFactory
from src.application.services.transformation.metadata import create_new_metadata, update_existing_metadata
from src.domain.models.metadata import Metadata
from src.infrastructure.db.mongo.mongo_adapter import MongoDBAdapter

logger = logging.getLogger("rs-etl-pipeline")

ALAMBIQUE = os.getenv('ALAMBIQUE', 'alambiqueDev')
PRETOOLS = os.getenv('PRETOOLS', 'pretoolsDev')
def get_identifier(entry: Dict) -> str:
    '''
    Extracts the identifier from a raw entry.

    Args:
        entry (dict): dictionary with the raw data
    '''
    identifier = entry.get('_id', None)
    if not identifier:
        logger.error(f"No identifier found for entry {entry}")
        return None
    return identifier

def standardize_entry(identifier: str,  raw: Dict, source: str) -> List[Dict]:
    
    if not identifier:
        logger.debug("No identifier found for entry; skipping...")
        return

    # Standardize the software metadata entries into the standard data model
    standardizer = MetadataStandardizerFactory.get_standardizer(source)
    tools = standardizer.process_transformation(raw)

    if tools:
        # To dictionary 
        tools_dicts = [inst.model_dump(mode="json") for inst in tools]
    else:
        tools_dicts = []

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
        logger.info(f"Creating metadata for entry {identifier}")
        logger.info(f"Source identifier: {source_identifier}")
        metadata = create_new_metadata(source_identifier, identifier, source_url, ALAMBIQUE)
    else:
        existing_metadata  = mongo_adapter.get_entry_metadata(PRETOOLS, identifier)
        existing_metadata = Metadata(**existing_metadata)
        metadata = update_existing_metadata(PRETOOLS, existing_metadata)
    
    metadata_dict = metadata.model_dump(mode="json")

    return metadata_dict



def save_entry(software_metadata_dict, raw_entry):
    '''
    Save the entry in the database
    '''
    # Generate metadata for the new metada entry
    source = software_metadata_dict['source'][0]
    name = software_metadata_dict['name']
    type = software_metadata_dict['type']
    version = software_metadata_dict['version'][0]
    identifier = f'{source}/{name}/{type}/{version}'
    
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
        logger.error(f"An error occurred while processing entry {identifier}: {e}")