# This adapter translates DB logic into domain logic 
from src.infrastructure.db.mongo_adapter import MongoDBAdapter

class PublicationsMetadataRepository:
    def __init__(self, db_adapter: MongoDBAdapter):
        self.db_adapter = db_adapter
        self.collection_name = "publications_metadata"

    def entry_exists(self, identifier: str) -> bool:
        return self.db_adapter.entry_exists(self.collection_name, identifier)

    def get_metadata(self, identifier: str):
        return self.db_adapter.get_entry_metadata(self.collection_name, identifier)

    def save_entry(self, document: dict):
        self.db_adapter.insert_one(self.collection_name, document)
