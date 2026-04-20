from infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


if __name__ == "__main__":
    result = mongo_adapter.get_collection("publicationsMetadataDev").update_many(
        {},
        {"$unset": {"data.citations": ""}},
    )

    print(f"Matched docs: {result.matched_count}")
    print(f"Modified docs: {result.modified_count}")