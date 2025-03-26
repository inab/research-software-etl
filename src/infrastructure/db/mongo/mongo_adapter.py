# infrastructure/db/mongo_adapter.py
# If database changes, for example to SQL, then only this file will change, while
# the repositories (in adpaters/db) will remain the same.


import os
import pymongo
import logging
from typing import Dict
from pymongo.errors import NetworkTimeout, AutoReconnect, CursorNotFound
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.infrastructure.db.mongo.database_adapter import DatabaseAdapter

logger = logging.getLogger("rs-etl-pipeline")

class MongoDBAdapter(DatabaseAdapter):
    _client = None  # Class variable to hold the single MongoClient instance

    def __init__(self, database=None):

        # avoid creating multiple connections
        if MongoDBAdapter._client is None:
            MongoDBAdapter._client = self._initialize_client()

        # Reuse the existing connection
        self.client = MongoDBAdapter._client

        # Use the provided database name or default
        self.db = self.client[self._get_database_name(database)]

    def _initialize_client(self):
        """Initialize MongoDB Client"""
        mongo_host = os.getenv('MONGO_HOST', 'localhost')
        mongo_port = os.getenv('MONGO_PORT', '27017')
        mongo_user = os.getenv('MONGO_USER')
        print(f"Mongo user from singleton: {mongo_user}")
        mongo_pass = os.getenv('MONGO_PWD')
        mongo_auth_src = os.getenv('MONGO_AUTH_SRC', 'admin')

        logger.info(f"Connecting to MongoDB at {mongo_host}:{mongo_port}")

        # Initialize MongoDB Client with AutoReconnect handling
        try:
            client = pymongo.MongoClient(
                host=[f'{mongo_host}:{mongo_port}'],
                username=mongo_user,
                password=mongo_pass,
                authSource=mongo_auth_src,
                authMechanism='SCRAM-SHA-256',
                maxPoolSize=100,
                serverSelectionTimeoutMS=5000  # Avoid indefinite hanging
            )
            # Test connection
            client.admin.command('ping')
            return client
        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise
        

    def _get_database_name(self, database):
        """Get database name from parameter or environment variable"""
        return database or os.getenv('MONGO_DB', 'oeb-research-software')


    
    @retry(
    retry=retry_if_exception_type((NetworkTimeout, AutoReconnect)),
    wait=wait_exponential(multiplier=1, min=1, max=10), 
    stop=stop_after_attempt(5),
    )
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


    @retry(
    retry=retry_if_exception_type((NetworkTimeout, AutoReconnect)),
    wait=wait_exponential(multiplier=1, min=1, max=10), 
    stop=stop_after_attempt(5),
    )
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
    


    @retry(
    retry=retry_if_exception_type((NetworkTimeout, AutoReconnect)),
    wait=wait_exponential(multiplier=1, min=1, max=10), 
    stop=stop_after_attempt(5),
    )
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
        logger.info("Updating entry in collection: %s", collection_name)
        collection.update_one(
            {'_id': identifier},  # Query matching the document to update
            {'$set': data}  # Fields to update
        )


    @retry(
    retry=retry_if_exception_type((NetworkTimeout, AutoReconnect, CursorNotFound)),
    wait=wait_exponential(multiplier=1, min=1, max=10), 
    stop=stop_after_attempt(5),
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
        logger.debug(f"Fetching entries from collection {collection_name} with query: {query}")
        collection = self.db[collection_name]

        try:
            document = collection.find(query, no_cursor_timeout=True).batch_size(100) # preventing automatic cursor timeout
            return list(document)

        except CursorNotFound:
            logger.error(f"Cursor was lost for query: {query}. Retrying...")
            raise # Retrying the operation

    @retry( 
            retry=retry_if_exception_type((NetworkTimeout, AutoReconnect, CursorNotFound)),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            stop=stop_after_attempt(5),
    )
    def fetch_paginated_entries(self, collection_name: str, query: Dict, page_size: int = 100):
        """
        Retrieve documents from a specified MongoDB collection that match a given query in paginated form.

        This function searches for all documents within the specified collection that match the criteria outlined in the query dictionary. It returns a cursor to the documents, which can be iterated over to access individual documents. This is typically used for fetching multiple documents rather than a single document.

        Args:
            collection_name (str): The name of the collection from which documents are to be retrieved.
            query (dict): A dictionary specifying the query criteria used to find documents. This must conform to MongoDB's query format.
            page_size (int): The number of documents to retrieve per page. Defaults to 100.
        
        Yields:
            List[Dict]: A list of documents that match the query, with each list representing a page of documents.
        """
        logger.debug(f"Fetching paginated entries from collection {collection_name} with query: {query}")
        collection = self.db[collection_name]
        skip = 0 

        while True:
            cursor = collection.find(query).skip(skip).limit(page_size)
            documents = list(cursor)
            if not documents:
                break # stops when no more documents are found

            yield documents
            skip += page_size # moves to the next page



    @retry(
    retry=retry_if_exception_type((NetworkTimeout, AutoReconnect)),
    wait=wait_exponential(multiplier=1, min=1, max=10), 
    stop=stop_after_attempt(5),
    )
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
    

    @retry(
    retry=retry_if_exception_type((NetworkTimeout, AutoReconnect)),
    wait=wait_exponential(multiplier=1, min=1, max=10), 
    stop=stop_after_attempt(5),
    )
    def insert_one(self, collection_name: str, document: Dict):
        """
        Insert a single document into a specified MongoDB collection.

        This function adds a new document to the specified collection in the MongoDB database. The document is provided as a dictionary, and the function does not return any value. The document will be inserted into the collection as a new entry.

        Args:
            collection_name (str): The name of the collection where the document will be inserted.
            document (dict): A dictionary representing the document to be added to the collection.

        """
        collection = self.db[collection_name]
        if 'id' in document:
            document['_id'] = document.pop('id')
        
        id_inserted_doc =  collection.insert_one(document)
        logger.info(f"Inserted document into collection {collection_name}")
        return id_inserted_doc.inserted_id
    