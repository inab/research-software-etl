import os
import logging
from bson import json_util 

from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from src.infrastructure.db.mongo.standardized_software_repository import StdSoftwareMetaRepository
from src.application.services.integration.group_entries import group_by_key_with_links
from src.application.services.integration.entries_recovery import recover_shared_name_link

logger = logging.getLogger("rs-etl-pipeline")

# collections 
PRETOOLS = os.getenv('PRETOOLS', 'pretoolsDev')


def fetch_pretools():
    """
    Get all entries from the pretools collection.
    Returns a list of dictionaries with the data field of each entry.
    """
    std_software_repo = StdSoftwareMetaRepository(mongo_adapter)

    # fetch entries 
    # IGNORE OPEB_METRICS and BIOCONDA (OPEB_TOOLS_BIOCONDA)
    logger.debug(f"Fetching entries from {PRETOOLS} collection")
    raw_entries = std_software_repo.get_standardized_software_data()

    # validated_documents = mongo_adapter.validate_pretools_data(documents) # do not validate for now
    entries = []
    
    logger.debug("Now turing cursor to list of entries")
    for entry in raw_entries:
        entries.append(entry)

    logger.debug("Entries fetched. Returning them to the caller")
    return entries


def write_json_util(file_name, data):
    """
    Write data to a JSON file. Uses the bson.json_util module to serialize the data.
    """
    with open(file_name, 'w') as f:
        s = json_util.dumps(data)
        f.write(s)


def grouping_and_recovery_process(grouped_entries_file):
    '''
    Group entries from the pretools collection and recover shared entries.
    
    Args:
    - grouped_entries_file (str): Path to the file containing grouped entries. Default is 'data/grouped.json'.

    Write the grouped entries to a JSON file.
    '''
    # ==================================================
    # 1. Fetch entries from the pretools collection
    # ==================================================
    logger.info('Fetching entries from pretools')
    entries = fetch_pretools()

    # ==================================================
    # 2. Group entries refering to the same software
    # ==================================================
    logger.info('Starting grouping process')
    grouped_by_key = group_by_key_with_links(entries)

    # ==================================================
    # 3. Merge groups on entries that share name and non-repository link/s
    # ==================================================
    logger.info('Merging groups of shared name and non-repository link') 
    grouped_instances = recover_shared_name_link(grouped_by_key)

    logger.info("Grouping and recovery process complete. Writing grouped entries to file.")
    write_json_util(grouped_entries_file, grouped_instances)

