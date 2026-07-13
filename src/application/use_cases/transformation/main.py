"""
Application use case: transform a raw software entry into standardized records.

This module defines the main transformation workflow for a raw source entry.
Given a raw entry and its source, the use case coordinates the processing of
publication metadata and software metadata, links the resulting publication
identifiers to the standardized software records, and persists the transformed
data.

Its responsibility is orchestration rather than normalization: the detailed
publication and software metadata transformation logic is delegated to the
corresponding helper modules and specialized services.
""" 


import logging
from typing import List, Dict
from infrastructure.config import PipelineConfig
from infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from application.use_cases.transformation.publications_processing import extract_publications, standardize_publications
from infrastructure.db.mongo.raw_software_repository import RawSoftwareMetadataRepository
from application.use_cases.transformation.software_metadata_processing import standardize_entry, save_entry

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


def process_publications(entry: Dict, source: str, config: PipelineConfig):
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
                publications_ids = standardize_publications(source, publications_ids, publication, config)
                logger.debug(f"Id of publication: {publications_ids}")

    return list(publications_ids)


def process_raw_entry(raw_entry, source, config: PipelineConfig):

    # Process publication metadata in the entry and push publications to the appropriate collection
    publication_ids = process_publications(raw_entry, source, config)

    # Standardize software metadata in the entry
    raw_identifier = get_identifier(raw_entry)
    software_metadata_dicts = standardize_entry(raw_identifier, raw_entry, source)

    # TODO Validate URLs of repositories and webpage
    # using functions in adapters/http/url_resolver.py

    for software_metadata_dict in software_metadata_dicts:

        # Add publication Ids to the dictionary
        software_metadata_dict['publication'] = publication_ids

        # Save the entry in the database
        save_entry(software_metadata_dict, raw_entry, config)

    return



def process_source(source: str, config: PipelineConfig):
    """
    Process each data source by retrieving and transforming data.

    Args:
        source (str): The data source to process.
        config (PipelineConfig): collections and paths for this run.

    This function logs the start of the data transformation, retrieves the raw data, and
    processes each entry if data is found. Logs if no data is found.
    """

    try:
        logger.info(f"Starting transformation of data from {source}")
        alambique_repo = RawSoftwareMetadataRepository(mongo_adapter, config.alambique_collection)
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
            process_raw_entry(raw_entry, source, config)

        # remaining batches
        for batch in raw_data:
            for raw_entry in batch:
                process_raw_entry(raw_entry, source, config)

    except Exception as e:
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



def transform_sources(sources: List[str], config: PipelineConfig, **kwargs):
    """
    Main function to orchestrate the transformation process for multiple sources.

    Args:
        sources (List[str]): A list of data sources to process.
        config (PipelineConfig): collections and paths for this run.
        **kwargs: Arbitrary keyword arguments.

    This function processes each source using a database adapter.
    """
    for source in sources:
        process_source(source, config)
