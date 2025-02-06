'''
Functions to create the metadata for the publication entries. To be inserted in the "publications" collection.
- import metadata entity
- create_metadata
- return metadata object
''' 
import os
from datetime import datetime
from src.domain.models.publication.metadata import Metadata
from datetime import datetime

def create_new_metadata(identifier: str, source_url: str = None,  collection: str = 'PublicationsDev') -> Dict:
    """
    Creates metadata for a new database entry.

    This function generates metadata for an entry that is not yet in the database. It sets both creation and last updated fields to the current date and time, and it includes URLs for creation and update logs based on the current environment variables.

    Parameters:
        identifier (str): The unique identifier for the new entry.
        collection (str): The collection name associated with the entry.

    Returns:
        Metadata: A Metadata dictionary with the current date and environment-specific values for a new entry.

    """
    current_date = datetime.now().isoformat()
    commit_url = build_commit_url()
    pipeline_url = os.getenv("CI_PIPELINE_URL")

    if not pipeline_url:
        pipeline_url = "local"
    if not commit_url:
        commit_url = "https://gitlab.com/evamdpico/research-software-meta/-/tree/4a4cdc3c2076f6f7c920c5de93d9d2563ec5bcba"

    metadata = Metadata(
        created_at=current_date,
        created_by=commit_url,
        created_logs=pipeline_url,
        last_updated_at=current_date,
        updated_by=commit_url,
        updated_logs=pipeline_url
    )

    metadata_dict = metadata.model_dump()

    return metadata_dict


def update_existing_metadata(identifier: str, existing_metadata: Metadata) -> Metadata:
    """
    Updates metadata for an existing database entry.

    This function updates the metadata for an existing entry, setting the last updated fields to the current date and time, and updating the URLs for the update logs based on current environment variables.

    Parameters:
        identifier (str): The unique identifier for the existing entry.
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
    
    return existing_metadata


def build_commit_url():
    CI_PROJECT_NAMESPACE = os.getenv("CI_PROJECT_NAMESPACE")
    CI_PROJECT_NAME = os.getenv("CI_PROJECT_NAME")
    CI_COMMIT_SHA = os.getenv("CI_COMMIT_SHA")
    return f"https://gitlab.bsc.es/{CI_PROJECT_NAMESPACE}/{CI_PROJECT_NAME}/-/commit/{CI_COMMIT_SHA}"
