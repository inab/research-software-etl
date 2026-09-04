"""
Application use case support: process software metadata during transformation.

This module contains the software-metadata part of the transformation
workflow. It standardizes raw source entries into one or more normalized
software metadata records, generates or updates the metadata required for
persistence, and inserts or updates the resulting records in the target
collection.

Its role is to ensure that raw source records are converted into the internal
software metadata representation and stored consistently in the database.
"""

import logging
from typing import List, Dict, Optional
from application.services.transformation.standardizers_factory import MetadataStandardizerFactory
from application.services.transformation.metadata import create_new_metadata, update_existing_metadata
from domain.models.metadata import Metadata
from infrastructure.config import PipelineConfig
from shared.utils import content_hash


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

def standardize_entry(identifier: str,  raw: Dict, source: str) -> List[Dict]:
    
    if not identifier:
        logger.debug("No identifier found for entry; skipping...")
        return

    # Standardize the software metadata entries into the standard data model
    standardizer = MetadataStandardizerFactory.get_standardizer(source)
    tools = standardizer.process_transformation(raw)

    if tools:
        # To dictionary 
        tools_dicts = [inst.model_dump(mode="json") for inst in tools]
    else:
        tools_dicts = []

    return(tools_dicts)


def pretools_identifier(software_metadata_dict: Dict) -> str:
    """The pretools ``_id`` for a standardized software record: ``source/name/type/version``."""
    source = software_metadata_dict['source'][0]
    name = software_metadata_dict['name']
    type = software_metadata_dict['type']

    if len(software_metadata_dict['version']) > 0:
        version = software_metadata_dict['version'][0]
    else:
        version = None

    return f'{source}/{name}/{type}/{version}'


def build_pretools_document(
    identifier: str,
    software_metadata_dict: Dict,
    raw_entry: Dict,
    existing_doc: Optional[Dict],
    config: PipelineConfig,
) -> Dict:
    """
    Build the pretools document to upsert for one standardized record -- purely,
    with no database access.

    ``existing_doc`` is the current pretools entry for this identifier (from a
    batched ``get_by_ids``) or ``None`` if there is none. When absent, fresh
    metadata is created. When present, its ``created_*`` provenance is always
    preserved, and the ``last_updated_*`` fields are bumped **only if the
    standardized ``data`` actually changed** -- compared by content fingerprint
    against ``existing_doc['data']``. An unchanged re-transform keeps the stored
    ``last_updated_at`` so the field marks the last real change, not the last run.

    The returned document carries no ``_id``/``id`` field: ``bulk_upsert`` writes
    it with ``$set`` and supplies ``_id`` through the query filter, so setting the
    immutable ``_id`` here would be rejected by MongoDB on update.
    """
    if existing_doc is None:
        source_url = raw_entry.get('@source_url', None)
        source_identifier = get_identifier(raw_entry)
        metadata = create_new_metadata(
            source_identifier,
            identifier,
            source_url,
            config.alambique_collection,
            config.ci,
        )
    else:
        meta_fields = {key: value for key, value in existing_doc.items() if key != 'data'}
        # The Metadata model keys the id as `id`; the stored doc keys it `_id`.
        if '_id' in meta_fields:
            meta_fields['id'] = meta_fields.pop('_id')

        unchanged = content_hash(existing_doc.get('data')) == content_hash(software_metadata_dict)
        if unchanged:
            # Content is identical to what is stored: preserve last_updated_* as-is.
            metadata = Metadata(**meta_fields)
        else:
            metadata = update_existing_metadata(Metadata(**meta_fields), config.ci)

    document = metadata.model_dump(mode="json")
    document.pop('id', None)
    document.pop('_id', None)
    document['data'] = software_metadata_dict

    return document