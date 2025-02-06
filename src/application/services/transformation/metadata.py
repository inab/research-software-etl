'''
Functions to create the metadata for the entries after transformation. To be inserted in the "pretools" collection.
- import metadata entity
- create_metadata
- return metadata object
''' 
import os
from datetime import datetime
from src.domain.models.metadata import Metadata
from datetime import datetime

def create_new_metadata(source_identifier, source_url: str = None,  alambique: str = 'alambiqueDev') -> Metadata:
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
        updated_logs=pipeline_url,
        source=[{
            "collection": alambique,
            "id": source_identifier,
            "source_url": source_url
        }]
    )
    return metadata


def update_existing_metadata(existing_metadata: Metadata) -> Metadata:
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
