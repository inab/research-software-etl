# infrastructure/mongo_adapter.py
import os
import pymongo
from typing import Dict, Any
from src.adapters.db.database_adapter import DatabaseAdapter
from src.core.domain.entities.database_entries import PretoolsEntryModel
from pydantic import ValidationError
import logging

class MongoDBAdapter(DatabaseAdapter):
    def __init__(self, database=None):
        # Load connection parameters from environment variables
        mongo_host = os.getenv('MONGO_HOST', default='localhost')
        mongo_port = os.getenv('MONGO_PORT', default='27017')
        mongo_user = os.getenv('MONGO_USER')
        mongo_pass = os.getenv('MONGO_PWD')
        mongo_auth_src = os.getenv('MONGO_AUTH_SRC', default='admin')

            # print environment variables
        logging.info(f"MongoDB host: {mongo_host}")
        logging.info(f"MongoDB port: {mongo_port}")
        logging.info(f"MongoDB user: {mongo_user}")
        logging.info(f"MongoDB password: {mongo_pass}")
        logging.info(f"MongoDB auth source: {mongo_auth_src}")

        if not database:
            mongo_db = os.getenv('MONGO_DB', default='oeb-research-software')
        else:
            mongo_db = database

        logging.debug(f"MongoDB database: {mongo_db}")

        # Connect to MongoDB using the specified parameters
        self.client = pymongo.MongoClient(
                host=[f'{mongo_host}:{mongo_port}'],
                username=mongo_user,
                password=mongo_pass,
                authSource=mongo_auth_src,
                authMechanism='SCRAM-SHA-256'
            )
        
        self.db = self.client[mongo_db]

    
    def entry_exists(self, collection_name: str, identifier: str) -> bool:
        """
        Check if an entry with the given identifier exists in the specified collection.

        This function queries the database for the presence of an entry by its identifier in the given collection. It returns True if the entry exists, otherwise False.

        Args:
            collection_name (str): The name of the collection within the database where the search will be performed.
            identifier (str): The identifier of the entry to search for in the collection.

        Returns:
            bool: True if an entry with the specified identifier exists in the collection, False otherwise.
        """
        collection = self.db[collection_name]
        query = { 
            '_id' : identifier 
        }
        return collection.count_documents(query) > 0

    def get_entry_metadata(self, collection_name: str, identifier: str) -> bool:
        """
        Retrieve metadata for an entry from the specified collection, excluding the 'data' field.

        Args:
            collection_name (str): The name of the MongoDB collection to query. This is where the entry will be searched.
            identifier (str): The unique identifier for the entry. This is used to find the specific entry in the collection.

        Returns:
            dict or None: A dictionary containing the metadata of the entry, excluding the 'data' field if the entry is found.
                        Returns None if no entry is found.
        """
        collection = self.db[collection_name]
        query = {
            '_id': identifier
        }
        projection = {
            'data': 0  # Exclude 'data' field
        }
        return collection.find_one(query, projection=projection)
    
    def update_entry(self, collection_name: str, identifier: str, data: dict):
        """
        Update specific fields of an entry in a given MongoDB collection.

        This function modifies an existing entry identified by a unique identifier in the specified collection. It updates fields of the entry according to the provided data dictionary. The function does not return any value, but it will update the first document that matches the identifier.

        Args:
            collection_name (str): The name of the MongoDB collection where the entry will be updated.
            identifier (str): The unique identifier for the entry to be updated. This is typically the MongoDB '_id' field value.
            data (dict): A dictionary containing the fields and values to be updated. Format should match MongoDB's update standards.
        """
        collection = self.db[collection_name]
        collection.update_one(
            {'_id': identifier},  # Query matching the document to update
            {'$set': data}  # Fields to update
        )

    def fetch_entries(self, collection_name: str, query: Dict):
        """
        Retrieve documents from a specified MongoDB collection that match a given query.

        This function searches for all documents within the specified collection that match the criteria outlined in the query dictionary. It returns a cursor to the documents, which can be iterated over to access individual documents. This is typically used for fetching multiple documents rather than a single document.

        Args:
            collection_name (str): The name of the collection from which documents are to be retrieved.
            query (dict): A dictionary specifying the query criteria used to find documents. This must conform to MongoDB's query format.

        Returns:
            pymongo.cursor.Cursor: A cursor for all documents that match the query, which allows for iterating over the documents found.
 
        """
        logging.debug(f"Fetching entries from collection {collection_name} with query: {query}")
        collection = self.db[collection_name]
        document = collection.find(query)
        return document
    
    def fetch_entry(self, collection_name: str, query: Dict):
        """
        Retrieve a single document from a specified MongoDB collection that matches a given query.

        This function searches for a single document within the specified collection that matches the criteria outlined in the query dictionary. It returns the document if found, or None if no matching document is located. This is typically used for fetching a single document based on specific criteria.

        Args:
            collection_name (str): The name of the collection from which the document is to be retrieved.
            query (dict): A dictionary specifying the query criteria used to find the document. This must conform to MongoDB's query format.

        Returns:
            dict or None: A dictionary representing the document that matches the query, or None if no matching document is found.

        """
        collection = self.db[collection_name]
        document = collection.find_one(query)
        return document
    

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
    
    def insert_one(self, collection_name: str, document: Dict):
        """
        Insert a single document into a specified MongoDB collection.

        This function inserts a single document into the specified collection within the MongoDB database. The document is provided as a dictionary and is added to the collection as a new entry. The function does not return any value, but it will add the document to the collection.

        Args:
            collection_name (str): The name of the MongoDB collection where the document will be inserted.
            document (dict): A dictionary representing the document to be added to the collection. This should conform to the structure expected by the collection.

        """
        collection = self.db[collection_name]
        collection.insert_one(document)
