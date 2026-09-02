# This repository connects to the pretools collection and performs specific operations on it.

import logging

from pydantic import ValidationError
from pymongo import UpdateOne

from domain.models.database_entries import PretoolsEntryModel
from infrastructure.db.database_adapter import DatabaseAdapter

logger = logging.getLogger("rs-etl-pipeline")


class PretoolsRepository:
    def __init__(self, db_adapter: DatabaseAdapter, collection_name: str = "pretoolsDev"):
        self.db_adapter = db_adapter
        self.collection_name = collection_name

    def get_all(self):
        logger.info('Fetching standardized software data from the pretools collection')
        standardized_software_data = self.db_adapter.fetch_entries(self.collection_name, {})
        logger.debug('Software obtained')
        return standardized_software_data

    def get_by_id(self, entry_id: str):
        """Return the full pretools entry with this id, or None."""
        return self.db_adapter.fetch_entry(self.collection_name, {"_id": entry_id})

    def get_by_ids(self, entry_ids) -> dict:
        """
        Fetch many entries at once, keyed by ``_id``.

        Replaces a per-id round-trip loop with a single ``$in`` query, paginated
        so a large id set does not build one enormous filter. Ids with no entry
        are simply absent from the returned dict.
        """
        unique_ids = list({entry_id for entry_id in entry_ids})
        by_id: dict = {}
        page_size = 1000
        for start in range(0, len(unique_ids), page_size):
            chunk = unique_ids[start : start + page_size]
            for entry in self.db_adapter.fetch_entries(
                self.collection_name, {"_id": {"$in": chunk}}
            ):
                by_id[entry["_id"]] = entry
        return by_id

    def exists(self, identifier: str) -> bool:
        return self.db_adapter.entry_exists(self.collection_name, identifier)

    def get_metadata(self, identifier: str):
        """Return the entry with this identifier, without its `data` field."""
        return self.db_adapter.get_entry_metadata(self.collection_name, identifier)

    def upsert(self, identifier: str, document: dict):
        """Update the entry if it is already there, insert it otherwise."""
        if self.exists(identifier):
            return self.db_adapter.update_entry(self.collection_name, identifier, document)
        return self.db_adapter.insert_one(self.collection_name, document)

    def bulk_upsert(self, docs_by_id: dict) -> None:
        """
        Upsert many entries in a single round-trip, keyed by ``_id``.

        Replaces a per-entry ``exists`` + ``update``/``insert`` loop (two or three
        round-trips each) with one ``bulk_write``. Each document is written with
        ``$set`` so an existing entry is updated in place and a missing one is
        inserted (``upsert=True``); the driver ``UpdateOne`` stays here in the
        repository, never leaking into the application layer.
        """
        operations = [
            UpdateOne({"_id": identifier}, {"$set": document}, upsert=True)
            for identifier, document in docs_by_id.items()
        ]
        if operations:
            self.db_adapter.bulk_write(self.collection_name, operations)

    def validate_standardized_software_data(self, documents):
        """
        Validate a list of documents using the PretoolsEntryModel schema and return the validated documents.

        This function iterates over a list of document dictionaries, attempting to validate each one according to the PretoolsEntryModel schema, which includes specific metadata and data fields. Validated documents are converted to their dictionary form and collected in a list. If a document fails validation, an error is logged and the document is skipped.

        Args:
            documents (list of dict): A list of dictionaries representing the documents to be validated. Each dictionary should include necessary fields that the PretoolsEntryModel schema expects.

        Returns:
            list of dict: A list containing the dictionary representations of all successfully validated documents. Documents that fail validation are not included.
        """
        validated_documents = []
        for doc in documents:
            try:
                validated_doc = PretoolsEntryModel(metadata=doc, data=doc['data'])
                validated_documents.append(validated_doc.dict())
            except ValidationError as ve:
                logger.error(f"Data validation failed for {doc}: {ve}")
                continue

        return validated_documents

    def get_bioconda_types(self):
        '''
        This function returns a dictionary with the types of the bioconda tools in the pretools collection.
        '''
        bioconda_types = {}
        try:
            bioconda_entries = self.db_adapter.fetch_entries(
                self.collection_name, {'data.source': ['bioconda']}
            )
        except Exception:
            logger.error('while generating bioconda_types: could not connect to the pretools collection')
        else:
            for tool in bioconda_entries:
                bioconda_types[tool['data']['name']] = tool['data']['type']

        return bioconda_types
