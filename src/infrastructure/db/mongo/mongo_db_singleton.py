from src.infrastructure.db.mongo.mongo_adapter import MongoDBAdapter
from src.infrastructure.db.mongo.publications_repository import PublicationsMetadataRepository


# This ensures only one instance exists in your application
mongo_adapter = MongoDBAdapter()