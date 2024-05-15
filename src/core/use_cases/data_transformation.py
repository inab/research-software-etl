import os
import logging 
from typing import List, Dict

from src.core.domain.services.transformation.standardizers_factory import MetadataStandardizerFactory
from src.core.domain.services.transformation.metadata import create_new_metadata, update_existing_metadata
from src.core.domain.entities.metadata import Metadata
from src.infrastructure.db.mongo_adapter import MongoDBAdapter
from src.adapters.db.database_adapter import DatabaseAdapter

# Variables for collection names:

PRETOOLS = os.getenv('PRETOOLS', 'pretools')
ALAMBIQUE = os.getenv('ALAMBIQUE', 'alambique')

# Code:
def get_raw_data_db(source: str, db_adapter: DatabaseAdapter) -> List[Dict]:
    '''
    Retrieve raw data from a specific source in the database.

    This function connects to a database using a provided database adapter and retrieves raw data from a specified source. The data is fetched from a database collection named by the 'ALAMBIQUE' environment variable, or 'alambique' if the variable is not set. This function logs the access attempt and returns the raw data as a list of dictionaries.

    Args:
        source (str): The label of the source from which to retrieve data. This determines the subset of data to be fetched from the database.
        db_adapter (DatabaseAdapter): An adapter used to facilitate connection to and interaction with the database.

    Returns:
        List[Dict]: A list of dictionaries, each representing an item of raw data retrieved from the specified source.

    Environment Variables:
        ALAMBIQUE (str): Defines the name of the database collection to query. Defaults to 'alambique' if not set.

    '''
    
    logging.debug(f"Accessing data of source {source} in db collection {ALAMBIQUE}")
    
    raw = db_adapter.get_raw_documents_from_source(ALAMBIQUE, source)
    
    return list(raw)


def standardize_entry(raw: Dict, source: str) -> List[Dict]:
    """
    Standardize raw entry data from a specified source into multiple instances of the 'software_instance' format.

    This function takes a dictionary representing raw data from a specific source and standardizes it into one or more dictionaries formatted according to the 'software_instance' model in the 'entities' module. The transformation is performed by a standardizer object from the StandardizersFactory, based on the source. This process may generate multiple standardized instances from a single raw input if the data includes elements that can be expanded into multiple records.

    Args:
        raw (Dict): A dictionary containing the raw data of an entry that needs to be standardized. The content of this dictionary is expected to be transformed into one or more instances based on the 'software_instance' model.
        source (str): The label of the source that determines which standardization rules to apply. This label guides the transformation process, ensuring that it is suitable for the data origin.

    Returns:
        List[Dict]: A list of dictionaries, each conforming to the 'software_instance' model from the 'entities' module. Each dictionary represents a standardized version of the input data or a part of it, structured as defined by the model.

    """
    standardizer = MetadataStandardizerFactory.get_standardizer(source)
    tools = standardizer.process_transformation(raw)
    
    return(tools)

def get_identifier(entry: Dict) -> str:
    '''
    Extracts the identifier from a raw entry.

    Args:
        entry (dict): dictionary with the raw data
    '''
    identifier = entry.get('_id', None)
    if not identifier:
        logging.error(f"No identifier found for entry {entry}")
        return None
    return identifier

def generate_metadata(identifier: str, db_adapter: DatabaseAdapter):
    """
    Generate or update metadata for a given identifier using a database adapter.

    This function checks if metadata for a given identifier exists in the PRETOOLS collection of a database. If the metadata exists, it is updated using the current metadata; if it does not exist, new metadata is created. The operation uses various helper functions and methods from the DatabaseAdapter to check existence, retrieve existing metadata, and to update or create metadata.

    Args:
        identifier (str): The unique identifier for which metadata is to be generated or updated.
        db_adapter (DatabaseAdapter): An adapter instance used to interact with the database. It must have 'entry_exist', 'get_entry_metadata', and appropriate update and creation methods implemented.

    Returns:
        Metadata: An instance of the Metadata class containing the generated or updated metadata.

    Raises:
        Exception: Specific exceptions can be raised depending on the implementation of database interaction methods in the DatabaseAdapter. For example, connectivity issues or data retrieval errors.

    """
    
    entry_exists_db = db_adapter.entry_exist(PRETOOLS, identifier )
    if entry_exists_db:
        metadata = create_new_metadata(identifier, PRETOOLS)
    else:
        existing_metadata  = db_adapter.get_entry_metadata(PRETOOLS, identifier)
        existing_metadata = Metadata(**existing_metadata)
        metadata = update_existing_metadata(identifier, PRETOOLS, existing_metadata)
    
    return metadata
    


def setup_logging(loglevel: int):
    """
    Configure the logging settings for the entire application.

    Args:
        loglevel (int): The logging level to use (e.g., logging.DEBUG, logging.INFO).

    This function sets the overall logging configuration based on the provided log level,
    specifically setting a quieter logging level for 'bibtexparser' to reduce verbosity.
    """
    logging.basicConfig(level=loglevel)
    logging.getLogger('bibtexparser').setLevel(logging.WARNING)

def process_source(source: str, db_adapter: DatabaseAdapter):
    """
    Process each data source by retrieving and transforming data.

    Args:
        source (str): The data source to process.
        db_adapter (DatabaseAdapter): The database adapter for database operations.

    This function logs the start of the data transformation, retrieves the raw data, and
    processes each entry if data is found. Logs if no data is found.
    """
    try:
        logging.info(f"Starting transformation of data from {source}")            
        raw_data = get_raw_data_db(source, db_adapter)

        if not raw_data:
            logging.info(f"No entries found for {source}")
            return

        logging.debug(f"Transforming raw tools metadata from {source}")
        for entry in raw_data:
            process_entry(entry, source, db_adapter)

    except Exception as e:
        logging.error(f"An error occurred while processing source {source}: {e}")


def process_entry(entry, source, db_adapter):
    """
    Process an individual entry from the data source.

    Args:
        entry (dict): The raw data entry to process.
        source (str): The data source of the entry.
        db_adapter (DatabaseAdapter): The database adapter for database operations.

    This function identifies, standardizes, and generates metadata for an entry,
    then updates the database. It skips processing if no identifier is found.
    """
    try:
        identifier = get_identifier(entry)
        if not identifier:
            logging.debug("No identifier found for entry; skipping...")
            return

        insts = standardize_entry(entry, source)
        metadata = generate_metadata(identifier, db_adapter)

        for inst in insts:
            document = metadata.to_dict_for_db_insertion()
            document['data'] = inst.__dict__
            db_adapter.update_entry(PRETOOLS, identifier, document)
    
    except Exception as e:
        logging.error(f"An error occurred while processing entry from {source}: {e}")

sources = [
    'biotools',
    'bioconda',
    'bioconda_recipes',
    'bioconductor',
    'galaxy_metadata',
    'toolshed',
    'galaxy',
    'sourceforge',
    'opeb_metrics'
]

def transform(loglevel: int = logging.WARNING, sources: List[str] = sources, **kwargs):
    """
    Main function to orchestrate the transformation process for multiple sources.

    Args:
        loglevel (int): The log level to use across the application. Defaults to logging.WARNING.
        sources (List[str]): A list of data sources to process. Defaults to the predefined list of sources.
        **kwargs: Arbitrary keyword arguments.

    This function sets up logging and processes each source using a database adapter.
    """
    setup_logging(loglevel)
    db_adapter = MongoDBAdapter()
    for source in sources:
        process_source(source, db_adapter)
