# infrastructure/mongo_adapter.py
import os
from pymongo import MongoClient

class MongoDBAdapter:
    def __init__(self):
        # Load connection parameters from environment variables
        mongo_host = os.getenv('MONGO_HOST', default='localhost')
        mongo_port = os.getenv('MONGO_PORT', default='27017')
        mongo_user = os.getenv('MONGO_USER')
        mongo_pass = os.getenv('MONGO_PWD')
        mongo_auth_src = os.getenv('MONGO_AUTH_SRC', default='admin')
        mongo_db = os.getenv('MONGO_DB', default='oeb-research-software')

        # Connect to MongoDB using the specified parameters
        
        self.client = MongoClient(
                host=[f'{mongo_host}:{mongo_port}'],
                username=mongo_user,
                password=mongo_pass,
                authSource=mongo_auth_src,
                authMechanism='SCRAM-SHA-256'
            )
        
        self.db = self.client[mongo_db]

    
    def entry_exists(self, collection_name, query):
        # Check if an entry exists in the specified collection based on the query
        collection = self.db[collection_name]
        return collection.count_documents(query) > 0

    # TODO: modify the following
    #def update_entry(self, collection_name, query, update_data):
        # Update an entry in the specified collection based on the query
    #    collection = self.db[collection_name]
    #    collection.update_one(query, {'$set': update_data})