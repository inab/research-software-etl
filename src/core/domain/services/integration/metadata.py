'''
Functions to create the metadata for the entries after integration. To be inserted in the "tools" collection.
''' 
import os
from typing import List
from datetime import datetime
from src.core.domain.entities.metadata import VersionedMetadata
from datetime import datetime

def create_new_metadata(identifier: str, pretools: str, source_identifiers: List) -> VersionedMetadata:
    """
    Creates metadata for a new database entry.

    This function generates metadata for an entry that is not yet in the database. It sets both creation and last updated fields to the current date and time, and it includes URLs for creation and update logs based on the current environment variables.

    Parameters:
        identifier (str): The unique identifier for the new entry.
        pretools (str): The collection name associated with the entry.

    Returns:
        Metadata: A Metadata object initialized with the current date and environment-specific values for a new entry.
    
    Example:
        >>> new_metadata = create_new_metadata("001", "tools")
        >>> print(new_metadata.created_at)
        '2023-10-04T14:48:00.123456'
    """
    current_date = datetime.now().isoformat()
    commit_url = build_commit_url()
    pipeline_url = os.getenv("CI_PIPELINE_URL")

    metadata = VersionedMetadata(
        created_at=current_date,
        created_by=commit_url,
        created_logs=pipeline_url,
        last_updated_at=current_date,
        updated_by=commit_url,
        updated_logs=pipeline_url,
        version=1,
        source={
            "collection": pretools,
            "ids": source_identifiers
        }
    )
    return metadata


def update_existing_metadata(existing_metadata: VersionedMetadata) -> VersionedMetadata:
    """
    Updates metadata for an existing database entry.

    This function updates the metadata for an existing entry, setting the last updated fields to the current date and time, and updating the URLs for the update logs based on current environment variables.

    Parameters:
        existing_metadata (Metadata): The current metadata object that needs to be updated.

    Returns:
        Metadata: The updated Metadata object with the new last updated time and URLs for update logs.
    
    Example:
        >>> existing_metadata = Metadata(created_at="2023-01-01T00:00:00Z", created_by="url1", ...)
        >>> updated_metadata = update_existing_metadata("001", "tools", existing_metadata)
        >>> print(updated_metadata.last_updated_at)
        '2023-10-04T14:48:00.123456'
    """
    current_date = datetime.now().isoformat()
    commit_url = build_commit_url()

    existing_metadata.last_updated_at = current_date
    existing_metadata.updated_by = commit_url
    existing_metadata.updated_logs = os.getenv("CI_PIPELINE_URL")
    existing_metadata.version += 1
    
    return existing_metadata


def build_commit_url():
    CI_PROJECT_NAMESPACE = os.getenv("CI_PROJECT_NAMESPACE")
    CI_PROJECT_NAME = os.getenv("CI_PROJECT_NAME")
    CI_COMMIT_SHA = os.getenv("CI_COMMIT_SHA")
    return f"https://gitlab.bsc.es/{CI_PROJECT_NAMESPACE}/{CI_PROJECT_NAME}/-/commit/{CI_COMMIT_SHA}"
