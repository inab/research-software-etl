import os
import logging 
from typing import List, Dict
from src.infrastructure.db.mongo_adapter import MongoDBAdapter
from src.application.use_cases.transformation.publications_helpers import extract_publications
from src.adapters.db.raw_software_repository import RawSoftwareMetadataRepository
from src.application.use_cases.transformation.software_metadata_helpers import standardize_entry, save_entry

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
    return


def process_publications(entry: Dict, source: str):
    sources_w_publication = ['bioconductor', 'biotools', 'toolshed']
    if source in sources_w_publication:
        extract_publications(entry, source)

    return


def process_raw_entry(raw_entry, source):
    # TODO Validate values in the software metadata entry (URLs)

    # Process publication metadata in the entry and push publications to the appropriate collection
    publication_ids = process_publications(raw_entry, source)

    # Standardize software metadata in the entry
    software_metadata_dicts = standardize_entry(raw_entry, source)

    for software_metadata_dict in software_metadata_dicts:
        
        # Add publication Ids to the dictionary
        software_metadata_dict['publications'] = publication_ids

        # Save the entry in the database
        save_entry(software_metadata_dict, raw_entry)
    
    return


def get_raw_data_db(source: str) -> List[Dict]:
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
    ALAMBIQUE = os.getenv('ALAMBIQUE', 'alambiqueDev')

    logging.debug(f"Accessing data of source {source} in db collection {ALAMBIQUE}")
    mongo_adapter = MongoDBAdapter()
    alambique_repo = RawSoftwareMetadataRepository(mongo_adapter)
    raw = alambique_repo.get_raw_documents_from_source(source)
    
    return raw


def process_source(source: str):
    """
    Process each data source by retrieving and transforming data.

    Args:
        source (str): The data source to process.

    This function logs the start of the data transformation, retrieves the raw data, and
    processes each entry if data is found. Logs if no data is found.
    """
    try:
        logging.info(f"Starting transformation of data from {source}")            
        raw_data = get_raw_data_db(source)

        if not raw_data:
            logging.info(f"No entries found for {source}")
            return

        logging.debug(f"Transforming raw tools metadata from {source}")
        for raw_entry in raw_data:
            process_raw_entry(raw_entry, source)
            
    except Exception as e:
        logging.error(f"An error occurred while processing source {source}: {e}")

    return


'''
sources = [
    'bioconda',
    'bioconda_recipes',
    'biotools',
    'bioconductor',
    'galaxy_metadata',
    'toolshed',
    'galaxy',
    'sourceforge',
    'opeb_metrics'
]
'''
sources = []

def transform_sources(loglevel: int = logging.DEBUG, sources: List[str] = sources, **kwargs):
    """
    Main function to orchestrate the transformation process for multiple sources.

    Args:
        loglevel (int): The log level to use across the application. Defaults to logging.WARNING.
        sources (List[str]): A list of data sources to process. Defaults to the predefined list of sources.
        **kwargs: Arbitrary keyword arguments.

    This function sets up logging and processes each source using a database adapter.
    """
    setup_logging(loglevel)
    for source in sources:
        process_source(source)
