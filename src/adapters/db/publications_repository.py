# This adapter translates DB logic into domain logic 
from src.infrastructure.db.mongo_adapter import MongoDBAdapter

class PublicationsMetadataRepository:
    def __init__(self, db_adapter: MongoDBAdapter):
        self.db_adapter = db_adapter
        self.collection_name = "publications_metadata"

    def find_by_doi(self, doi: str):
        """Find a publication metadata entry by DOI."""
        query = {"doi": doi}
        return self.db_adapter.fetch_entry(self.collection_name, query)
    

    def entry_exists(self, identifier: str) -> bool:
        return self.db_adapter.entry_exists(self.collection_name, identifier)

    def get_metadata(self, identifier: str):
        return self.db_adapter.get_entry_metadata(self.collection_name, identifier)

    def save_entry(self, document: dict):
        self.db_adapter.insert_one(self.collection_name, document)
