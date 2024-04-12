'''
Functions to create the metadata for the entries after transformation. To be inserted in the "pretools" collection.
- import metadata entity
- create_metadata
- return metadata object
''' 
import os
from datetime import datetime
from pymongo.collection import Collection
from src.core.domain.entities.metadata.pretools import Metadata
from src.infrastructure.db.mongo_adapter import MongoDBAdapter
def create_metadata(identifier: str, alambique:Collection, pretools:Collection):
    '''
    This function first checks if the entry is already in the database.
    If the entry is in the database, it creates a metadata dictionary with the 
    following fields:
        - "last_updated_at" : current_date
        - "updated_by" : task_run_id
    If the entry is not in the database, in addition the the previos fields,it:
    adds the following:
        - "created_at" : current_date
        - "created_by" : task_run_id
    The metadata is returned.
    '''
    # Current timestamp
    current_date = datetime.utcnow()
    # Commit url
    CI_PROJECT_NAMESPACE = os.getenv("CI_PROJECT_NAMESPACE")
    CI_PROJECT_NAME = os.getenv("CI_PROJECT_NAME")
    CI_COMMIT_SHA = os.getenv("CI_COMMIT_SHA")
    commit_url = f"https://gitlab.bsc.es/{CI_PROJECT_NAMESPACE}/{CI_PROJECT_NAME}/-/commit/{CI_COMMIT_SHA}"
    # Prepare the metadata to add or update

    # Check if the entry exists in the database
    adapter = MongoDBAdapter()
    existing_entry = adapter.entry_exists(alambique, {"_id": identifier})
    
    # Initiate object of the metadata entity
    metadata = Metadata(
        last_updated_at = current_date,
        updated_by = commit_url,
        updated_logs = os.getenv("CI_PIPELINE_URL"),
        source = {
            "collection": alambique.name,
            "_id": identifier
        }
    )

    if not existing_entry:
        # Add creation metadata
        metadata.created_at = current_date
        metadata.created_by = commit_url
        metadata.created_logs = os.getenv("CI_PIPELINE_URL")
        
    # Return the entry with the new fields
    return metadata

