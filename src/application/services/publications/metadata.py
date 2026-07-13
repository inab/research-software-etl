'''
Functions to create the metadata for the publication entries. To be inserted in the "publications" collection.
- import metadata entity
- create_metadata
- return metadata object
'''
from datetime import datetime
from domain.models.publication.metadata import Metadata
from infrastructure.config import CIContext
from typing import Dict


def create_new_metadata(ci: CIContext = None) -> Dict:
    """
    Creates metadata for a new database entry.

    Sets both creation and last updated fields to the current date and time, and
    records the commit and pipeline the entry came from.

    Parameters:
        ci (CIContext): provenance of the current run.

    Returns:
        Metadata: A Metadata dictionary with the current date and run-specific values.
    """
    ci = ci or CIContext()
    current_date = datetime.now().isoformat()

    metadata = Metadata(
        created_at=current_date,
        created_by=ci.commit_url(),
        created_logs=ci.logs_url(),
        last_updated_at=current_date,
        updated_by=ci.commit_url(),
        updated_logs=ci.logs_url()
    )

    return metadata.model_dump()


def update_existing_metadata(
    identifier: str, existing_metadata: Metadata, ci: CIContext = None
) -> Metadata:
    """
    Updates metadata for an existing database entry.

    Sets the last updated fields to the current date and time, and records the
    commit and pipeline of the current run.

    Parameters:
        identifier (str): The unique identifier for the existing entry.
        existing_metadata (Metadata): The current metadata object that needs to be updated.
        ci (CIContext): provenance of the current run.

    Returns:
        Metadata: The updated Metadata object.
    """
    ci = ci or CIContext()

    existing_metadata.last_updated_at = datetime.now().isoformat()
    existing_metadata.updated_by = ci.commit_url()
    existing_metadata.updated_logs = ci.logs_url()

    return existing_metadata


def build_commit_url(ci: CIContext = None) -> str:
    return (ci or CIContext()).commit_url()
