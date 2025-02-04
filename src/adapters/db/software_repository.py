# This adapter translates DB logic into domain logic from src.infrastructure.mongo_adapter import MongoDBAdapter

from src.infrastructure.db.mongo_adapter import MongoDBAdapter
from src.core.domain.entities.database_entries import PretoolsEntryModel
from pydantic import ValidationError
import logging

class SoftwareMetadataRepository:
    def __init__(self, db_adapter: MongoDBAdapter):
        self.db_adapter = db_adapter
        self.collection_name = "software_metadata"

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
    

    def build_raw_docs_query(self, source: str):
        """
        Construct a query dictionary for retrieving documents from a "alambique" db collection based on their source.

        Args:
            source (str): The data source to be queried in the database. This is used to match the '@data_source' field in the documents.

        Returns:
            dict: A query dictionary that can be used with MongoDB to find documents that have a matching '@data_source' field.

        """
        query = {
            '@data_source': source
        }
        return query


    def get_raw_documents_from_source(self, collection_name: str, source: str) -> Dict[str, Any]:
        """
        Retrieve and return documents from a specified MongoDB collection that match a particular source.

        This function constructs a query using the `build_raw_docs_query` method with the provided source parameter. It then uses this query to fetch entries from the specified collection using the `fetch_entries` method. The function returns all documents matching the query, typically used for processing raw data from various sources.

        Args:
            collection_name (str): The name of the MongoDB collection from which documents are to be retrieved.
            source (str): The source identifier used to generate the query for fetching documents. Documents in the collection that match this source will be retrieved.

        Returns:
            dict: A dictionary containing all documents from the specified collection that match the given source, structured as raw data entries.

        """
        query = self.build_raw_docs_query(source)
        raw_data = self.fetch_entries(collection_name, query)

        return raw_data
    
    