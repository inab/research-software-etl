# Raw software repository# This adapter translates DB logic into domain logic from src.infrastructure.mongo_adapter import MongoDBAdapter

from src.infrastructure.db.mongo.mongo_adapter import MongoDBAdapter
from typing import Dict, Any

class RawSoftwareMetadataRepository:
    def __init__(self, db_adapter: MongoDBAdapter):
        self.db_adapter = db_adapter
        self.collection_name = "alambiqueDev"


    def get_raw_documents_from_source(self,source: str) -> Dict[str, Any]:
        """
        Retrieve and return documents from a specified MongoDB collection that match a particular source.

        This function constructs a query using the `build_raw_docs_query` method with the provided source parameter. It then uses this query to fetch entries from the specified collection using the `fetch_entries` method. The function returns all documents matching the query, typically used for processing raw data from various sources.

        Args:
            source (str): The source identifier used to generate the query for fetching documents. Documents in the collection that match this source will be retrieved.

        Returns:
            pymongo.cursor.Cursor: A cursor for all documents that match the query, which allows for iterating over the documents found.
        """
        raw_data = self.db_adapter.fetch_entries(self.collection_name, {'@data_source': source})

        return raw_data
    
    