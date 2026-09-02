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
from datetime import datetime
from typing import List, Dict, Optional
from infrastructure.config import PipelineConfig
from domain.repositories import Repositories
from application.use_cases.transformation.publications_processing import resolve_publications_for_page
from application.use_cases.transformation.software_metadata_processing import (
    standardize_entry,
    pretools_identifier,
    build_pretools_document,
)

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


def process_page(raw_entries: List[Dict], source: str, config: PipelineConfig, repos: Repositories):
    """
    Transform one page of raw entries with a fixed, small number of DB round-trips.

    Everything that can be done in memory (standardization) is done first; the
    database is then touched only in batches: one publication lookup per identifying
    field, one insert for the page's new publications, one ``get_by_ids`` for the
    page's pretools ids, and one ``bulk_upsert`` to write them. This replaces the
    old per-entry path that issued several latency-bound round-trips per entry.
    """
    if not raw_entries:
        return

    # 1. Standardize software metadata for every entry -- in memory, no DB.
    standardized_per_entry: List[List[Dict]] = []
    for raw_entry in raw_entries:
        raw_identifier = get_identifier(raw_entry)
        software_dicts = standardize_entry(raw_identifier, raw_entry, source)
        standardized_per_entry.append(software_dicts or [])

    # 2. Resolve this page's publications in a handful of batched round-trips.
    publication_ids_by_entry = resolve_publications_for_page(raw_entries, source, config, repos)

    # 3. Flatten to the pretools records to write, attaching publication ids.
    inputs: List[tuple] = []  # (identifier, software_dict, raw_entry)
    for entry_index, software_dicts in enumerate(standardized_per_entry):
        publication_ids = publication_ids_by_entry[entry_index]
        raw_entry = raw_entries[entry_index]
        for software_dict in software_dicts:
            software_dict['publication'] = publication_ids
            inputs.append((pretools_identifier(software_dict), software_dict, raw_entry))

    if not inputs:
        return

    # 4. One existence query for the whole page (replaces per-entry exists/get_metadata).
    existing = repos.pretools.get_by_ids([identifier for identifier, _, _ in inputs])

    # 5. Build documents purely, then one bulk upsert for the page.
    docs_by_id: Dict[str, Dict] = {}
    for identifier, software_dict, raw_entry in inputs:
        docs_by_id[identifier] = build_pretools_document(
            identifier, software_dict, raw_entry, existing.get(identifier), config
        )

    repos.pretools.bulk_upsert(docs_by_id)


def process_source(
    source: str,
    config: PipelineConfig,
    repos: Repositories,
    updated_since: Optional[datetime] = None,
):
    """
    Process each data source by retrieving and transforming data.

    Args:
        source (str): The data source to process.
        config (PipelineConfig): collections and paths for this run.
        repos (Repositories): the collections this stage reads and writes.
        updated_since (datetime, optional): only transform entries whose
            ``@last_updated_at`` is on or after this datetime; ``None`` transforms
            every entry for the source.

    This function logs the start of the data transformation, retrieves the raw data
    one page at a time, and transforms each page. Logs if no data is found. A page
    that fails is logged and skipped so the rest of the source still transforms.
    """
    logger.info(f"Starting transformation of data from {source}")
    raw_data = repos.alambique.get_raw_documents_from_source(source, updated_since=updated_since)

    pages = 0
    entries = 0
    for page in raw_data:
        pages += 1
        entries += len(page)
        try:
            process_page(page, source, config, repos)
        except Exception as e:
            logger.error(f"An error occurred while processing a page of source {source}: {e}")

    if pages == 0:
        logger.info(f"No data found for source {source}")
    else:
        logger.info(f"Transformed {entries} raw entries from {source} across {pages} page(s)")

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



def transform_sources(
    sources: List[str],
    config: PipelineConfig,
    repos: Repositories,
    updated_since: Optional[datetime] = None,
    **kwargs,
):
    """
    Main function to orchestrate the transformation process for multiple sources.

    Args:
        sources (List[str]): A list of data sources to process.
        config (PipelineConfig): collections and paths for this run.
        repos (Repositories): the collections this stage reads and writes.
        updated_since (datetime, optional): only transform entries whose
            ``@last_updated_at`` is on or after this datetime; ``None`` transforms
            every entry.
        **kwargs: Arbitrary keyword arguments.
    """
    for source in sources:
        process_source(source, config, repos, updated_since=updated_since)
