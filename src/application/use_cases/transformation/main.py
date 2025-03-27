import os
import logging 
from typing import List, Dict
from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from src.application.use_cases.transformation.publications_processing import extract_publications, standardize_publications
from src.infrastructure.db.mongo.raw_software_repository import RawSoftwareMetadataRepository
from src.application.use_cases.transformation.software_metadata_processing import standardize_entry, save_entry

logger = logging.getLogger("rs-etl-pipeline")

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
    '''
    TODO: test this function
    '''
    sources_w_publication = ['bioconductor', 'biotools', 'toolshed', 'opeb_metrics', 'bioconda_recipes']
    publications_ids = set()
    if source in sources_w_publication:
        logger.debug(f"Processing publications for entry {entry['_id']}")
        publications = extract_publications(source, entry)
        if len(publications) > 0:
            logger.debug(f"Found {len(publications)} publications for entry {entry['_id']}")
            for publication in publications:
                publications_ids = standardize_publications(source, publications_ids, publication)
                logger.debug(f"Id of publication: {publications_ids}")

    return list(publications_ids)


def process_raw_entry(raw_entry, source):

    # Process publication metadata in the entry and push publications to the appropriate collection
    publication_ids = process_publications(raw_entry, source)

    # Standardize software metadata in the entry
    raw_identifier = get_identifier(raw_entry)
    software_metadata_dicts = standardize_entry(raw_identifier, raw_entry, source)

    # TODO Validate URLs of repositories and webpage
    # using functions in adapters/http/url_resolver.py 

    for software_metadata_dict in software_metadata_dicts:
        
        # Add publication Ids to the dictionary
        software_metadata_dict['publication'] = publication_ids

        # Save the entry in the database
        save_entry(software_metadata_dict, raw_entry)
    
    return



def process_source(source: str):
    """
    Process each data source by retrieving and transforming data.

    Args:
        source (str): The data source to process.

    This function logs the start of the data transformation, retrieves the raw data, and
    processes each entry if data is found. Logs if no data is found.
    """
    

    try:
        logger.info(f"Starting transformation of data from {source}")            
        alambique_repo = RawSoftwareMetadataRepository(mongo_adapter)
        raw_data = alambique_repo.get_raw_documents_from_source(source)

        # checking if first batch has data
        try:
            first_batch = next(raw_data)
        except StopIteration:
            logger.info(f"No data found for source {source}")
            return

        logger.debug(f"Transforming raw tools metadata from {source}")

        # first batch 
        for raw_entry in first_batch:
            process_raw_entry(raw_entry, source)

        # remaining batches
        for batch in raw_data:
            for raw_entry in batch:
                process_raw_entry(raw_entry, source)
 
    except Exception as e:
        raise e
        logger.error(f"An error occurred while processing source {source}: {e}")

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



def transform_sources(sources: List[str], **kwargs):
    """
    Main function to orchestrate the transformation process for multiple sources.

    Args:
        loglevel (int): The log level to use across the application. Defaults to logging.WARNING.
        sources (List[str]): A list of data sources to process. Defaults to the predefined list of sources.
        **kwargs: Arbitrary keyword arguments.

    This function sets up logging and processes each source using a database adapter.
    """
    for source in sources:
        process_source(source)
