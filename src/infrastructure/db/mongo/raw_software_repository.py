# Raw software repository# This adapter translates DB logic into domain logic from infrastructure.mongo_adapter import MongoDBAdapter

from datetime import datetime
from typing import Optional

from infrastructure.db.mongo.mongo_adapter import MongoDBAdapter

class RawSoftwareMetadataRepository:
    def __init__(self, db_adapter: MongoDBAdapter, collection_name: str = "alambiqueDev"):
        self.db_adapter = db_adapter
        self.collection_name = collection_name


    def get_raw_documents_from_source(self, source: str, updated_since: Optional[datetime] = None):
        """
        Retrieve and return documents from a specified MongoDB collection that match a particular source.

        This function constructs a query matching the given source and, optionally, restricting to documents whose `@last_updated_at` is on or after `updated_since`. It then uses this query to fetch entries from the specified collection using the `fetch_paginated_entries` method. The function returns all documents matching the query, typically used for processing raw data from various sources.

        Args:
            source (str): The source identifier used to generate the query for fetching documents. Documents in the collection that match this source will be retrieved.
            updated_since (datetime, optional): When provided, only documents whose `@last_updated_at` is greater than or equal to this datetime are returned. When ``None`` (the default), every document for the source is returned.

        Returns:
            Generator.
        """
        query = {'@data_source': source}
        if updated_since is not None:
            query['@last_updated_at'] = {'$gte': updated_since}

        raw_data = self.db_adapter.fetch_paginated_entries(self.collection_name, query)

        return raw_data
    
    