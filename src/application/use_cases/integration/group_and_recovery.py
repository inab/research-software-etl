import os
import logging
from bson import json_util 

from infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from infrastructure.db.mongo.standardized_software_repository import StdSoftwareMetaRepository
from application.services.integration.group_entries import group_by_key_with_links
from application.services.integration.entries_recovery import recover_shared_name_link
from application.services.integration.group_split_corrections import apply_manual_split_corrections

logger = logging.getLogger("rs-etl-pipeline")

# collections 
PRETOOLS = os.getenv('PRETOOLS', 'pretoolsDev')
GROUP_SPLIT_CORRECTIONS_FILE = os.getenv(
    "GROUP_SPLIT_CORRECTIONS_FILE",
    "data/integration/manual_group_split_corrections.json",
)


def fetch_pretools():
    """
    Get all entries from the pretools collection.
    Returns a list of dictionaries with the data field of each entry.
    """
    std_software_repo = StdSoftwareMetaRepository(mongo_adapter)

    logger.debug(f"Fetching entries from {PRETOOLS} collection")
    raw_entries = std_software_repo.get_standardized_software_data()

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
    - grouped_entries_file (str): Path to the file containing grouped entries.

    Write the grouped entries to a JSON file.
    '''
    # ==================================================
    # 1. Fetch entries from the pretools collection
    # ==================================================
    logger.info('Fetching entries from pretools')
    entries = fetch_pretools()

    # ==================================================
    # 2. Group entries referring to the same software
    # ==================================================
    logger.info('Starting grouping process')
    grouped_by_key = group_by_key_with_links(entries)

    # ==================================================
    # 3. Merge groups on entries that share name and non-repository link/s
    # ==================================================
    logger.info('Merging groups of shared name and non-repository link')
    grouped_instances = recover_shared_name_link(grouped_by_key)

    # ==================================================
    # 4. Split groups using manual correction rules
    # ==================================================
    logger.info('Applying manual split corrections')
    grouped_instances = apply_manual_split_corrections(
        grouped_instances,
        GROUP_SPLIT_CORRECTIONS_FILE,
    )

    logger.info("Grouping and recovery process complete. Writing grouped entries to file.")
    write_json_util(grouped_entries_file, grouped_instances)