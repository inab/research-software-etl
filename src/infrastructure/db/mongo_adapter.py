# infrastructure/mongo_adapter.py
import os
import pymongo
from src.adapters.db.database_adapter import DatabaseAdapter

class MongoDBAdapter(DatabaseAdapter):
    def __init__(self):
        # Load connection parameters from environment variables
        mongo_host = os.getenv('MONGO_HOST', default='localhost')
        mongo_port = os.getenv('MONGO_PORT', default='27017')
        mongo_user = os.getenv('MONGO_USER')
        mongo_pass = os.getenv('MONGO_PWD')
        mongo_auth_src = os.getenv('MONGO_AUTH_SRC', default='admin')
        mongo_db = os.getenv('MONGO_DB', default='oeb-research-software')

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
        # Check if an entry exists in the specified collection based on the query
        collection = self.db[collection_name]
        query = { 
            '_id' : identifier 
        }
        return collection.count_documents(query) > 0

    def get_entry_metadata(self, collection_name: str, identifier: str) -> bool:
        # Retrieve an entry from the specified collection based on the query
        collection = self.db[collection_name]
        query = {
            '_id': identifier
        }
        projection = {
            'data': 0  # Exclude 'data' field
        }
        return collection.find_one(query, projection=projection)
    
    def update_entry(self, collection_name, identifier, data):
        collection = self.db[collection_name]
        collection.update_one(
            {'_id': identifier},  # Query matching the document to update
            {'$set': data}  # Fields to update
        )
