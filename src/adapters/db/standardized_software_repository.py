# This adapter translates DB logic into domain logic from src.infrastructure.mongo_adapter import MongoDBAdapter

from src.infrastructure.db.mongo_adapter import MongoDBAdapter
from src.domain.models.database_entries import PretoolsEntryModel
from pydantic import ValidationError
import logging

class StdSoftwareMetaRepository:
    def __init__(self, db_adapter: MongoDBAdapter):
        self.db_adapter = db_adapter
        self.collection_name = "pretoolsDev"

    def validate_pretools_data(self, documents):
        """
        Validate a list of documents using the PretoolsEntryModel schema and return the validated documents.

        This function iterates over a list of document dictionaries, attempting to validate each one according to the PretoolsEntryModel schema, which includes specific metadata and data fields. Validated documents are converted to their dictionary form and collected in a list. If a document fails validation, an error is logged and the document is skipped.

        Args:
            documents (list of dict): A list of dictionaries representing the documents to be validated. Each dictionary should include necessary fields that the PretoolsEntryModel schema expects.

        Returns:
            list of dict: A list containing the dictionary representations of all successfully validated documents. Documents that fail validation are not included.

        Raises:
            ValidationError: If a document fails validation, it logs the specific error and continues with the next document. This function itself does not raise the exception but handles it internally.

        """
        validated_documents = []
        for doc in documents:
            try:
                validated_doc = PretoolsEntryModel(metadata=doc, data=doc['data'])
                validated_documents.append(validated_doc.dict)
            except ValidationError as ve:
                logging.error(f"Data validation failed for {doc}: {ve}")
                continue  

        return validated_documents
