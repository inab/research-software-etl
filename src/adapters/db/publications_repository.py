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
    
    def find_by_title(self, title: str):
        """Find a publication metadata entry by title."""
        query = {"title": title}
        return self.db_adapter.fetch_entry(self.collection_name, query)

    def find_by_url(self, url: str):
        """Find a publication metadata entry by URL."""
        query = {"url": url}
        return self.db_adapter.fetch_entry(self.collection_name, query)

    def find_by_pmid(self, pmid: str):
        """Find a publication metadata entry by PMID."""
        query = {"pmid": pmid}
        return self.db_adapter.fetch_entry(self.collection_name, query)

    def find_by_pmcid(self, pmcid: str):
        """Find a publication metadata entry by PMCID."""
        query = {"pmcid": pmcid}
        return self.db_adapter.fetch_entry(self.collection_name, query)

    def entry_exists(self, identifier: str) -> bool:
        return self.db_adapter.entry_exists(self.collection_name, identifier)

    def get_metadata(self, identifier: str):
        return self.db_adapter.get_entry_metadata(self.collection_name, identifier)

    def save_entry(self, document: dict):
        self.db_adapter.insert_one(self.collection_name, document)
