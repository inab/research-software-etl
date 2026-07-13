'''
Functions to create the metadata for the entries after transformation. To be inserted in the "pretools" collection.
- import metadata entity
- create_metadata
- return metadata object
'''
from datetime import datetime
from domain.models.metadata import Metadata
from infrastructure.config import CIContext


def create_new_metadata(
    source_identifier,
    identifier,
    source_url: str = None,
    alambique: str = 'alambiqueDev',
    ci: CIContext = None,
) -> Metadata:
    ci = ci or CIContext()
    current_date = datetime.now().isoformat()

    metadata = Metadata(
        id=identifier,
        created_at=current_date,
        created_by=ci.commit_url(),
        created_logs=ci.logs_url(),
        last_updated_at=current_date,
        updated_by=ci.commit_url(),
        updated_logs=ci.logs_url(),
        source=[{
            "collection": alambique,
            "id": source_identifier,
            "source_url": source_url
        }]
    )
    return metadata


def update_existing_metadata(existing_metadata: Metadata, ci: CIContext = None) -> Metadata:
    ci = ci or CIContext()

    existing_metadata.last_updated_at = datetime.now().isoformat()
    existing_metadata.updated_by = ci.commit_url()
    existing_metadata.updated_logs = ci.logs_url()

    return existing_metadata


def build_commit_url(ci: CIContext = None) -> str:
    return (ci or CIContext()).commit_url()
