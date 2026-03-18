# This adapter translates DB logic into domain logic 
from src.infrastructure.db.mongo.mongo_adapter import MongoDBAdapter
from typing import Any, Iterable

from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


class MongoPublicationRepository:
    def __init__(self, mongo_db=mongo_adapter):
        self.mongo_db = mongo_db
        self.collection_name = "publicationsMetadataDev"

    def find_by_doi(self, doi: str):
        """Find a publication metadata entry by DOI."""
        query = {"data.doi": doi}
        return self.db_adapter.fetch_entry(self.collection_name, query)
    
    def find_by_title(self, title: str):
        """Find a publication metadata entry by title."""
        query = {"data.title": title}
        return self.db_adapter.fetch_entry(self.collection_name, query)

    def find_by_url(self, url: str):
        """Find a publication metadata entry by URL."""
        query = {"data.url": url}
        return self.db_adapter.fetch_entry(self.collection_name, query)

    def find_by_pmid(self, pmid: str):
        """Find a publication metadata entry by PMID."""
        query = {"data.pmid": pmid}
        return self.db_adapter.fetch_entry(self.collection_name, query)

    def find_by_pmcid(self, pmcid: str):
        """Find a publication metadata entry by PMCID."""
        query = {"data.pmcid": pmcid}
        return self.db_adapter.fetch_entry(self.collection_name, query)

    def entry_exists(self, identifier: str) -> bool:
        return self.db_adapter.entry_exists(self.collection_name, identifier)

    def get_metadata(self, identifier: str):
        return self.db_adapter.get_entry_metadata(self.collection_name, identifier)

    def save_entry(self, document: dict):
        return self.db_adapter.insert_one(self.collection_name, document)
    
    def fetch_with_doi(self, collection_name: str) -> Iterable[dict[str, Any]]:
        query = {"data.doi": {"$exists": True}}
        return self.mongo_db.fetch_entries(collection_name, query)

    def update_publication_data(
        self,
        collection_name: str,
        document_id: Any,
        data: dict[str, Any],
        last_updated_at: str,
    ) -> None:
        self.mongo_db.update_entry(
            collection_name,
            document_id,
            {
                "data": data,
                "last_updated_at": last_updated_at,
            },
        )
