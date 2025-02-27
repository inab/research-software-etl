# infrastructure/db/mongo_adapter.py
# If database changes, for example to SQL, then only this file will change, while
# the repositories (in adpaters/db) will remain the same.


import os
import pymongo
from typing import Dict
from src.infrastructure.db.mongo.database_adapter import DatabaseAdapter
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
        # logging.info(f"MongoDB host: {mongo_host}")
        # logging.info(f"MongoDB port: {mongo_port}")
        # logging.info(f"MongoDB user: {mongo_user}")
        # logging.info(f"MongoDB password: {mongo_pass}")
        # logging.info(f"MongoDB auth source: {mongo_auth_src}")

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
        logging.info("Updating entry in collection: %s", collection_name)
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
        logging.info(f"Inserted document into collection {collection_name}")
        return id_inserted_doc.inserted_id
    