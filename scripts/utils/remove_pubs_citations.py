from infrastructure.db.mongo.mongo_adapter import MongoDBAdapter

mongo_adapter = MongoDBAdapter()


if __name__ == "__main__":
    result = mongo_adapter.get_collection("publicationsMetadataDev").update_many(
        {},
        {"$unset": {"data.citations": ""}},
    )

    print(f"Matched docs: {result.matched_count}")
    print(f"Modified docs: {result.modified_count}")