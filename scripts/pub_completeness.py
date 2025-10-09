from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from bson import ObjectId

n=0
for record in mongo_adapter.fetch_entries("toolsDev", {}):
    if 'publication' in record['data']:
        publication = record['data']['publication']
        new_pub = []
        for pub_id in publication:
            pub = mongo_adapter.fetch_entry("publicationsMetadataDev", {"_id": ObjectId(pub_id)})
            if pub:
                new_pub.append(pub_id)
            else:
                n += 1
        
        mongo_adapter.update_entry("toolsDev", record['_id'], {'data.publication' : new_pub})

print(f"Updated {n} records with invalid publication IDs.")