from src.infrastructure.db.mongo.mongo_adapter import MongoDBAdapter


# This ensures only one instance exists in your application
mongo_adapter = MongoDBAdapter()