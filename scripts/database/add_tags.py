from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


n = 0
n_pretools = 0
n_tools = 0
# For each entry from biotools in alambiqueDev
for entry in mongo_adapter.fetch_entries("alambiqueDev", {"@data_source": "biotools"}):
    n += 1
    # get ID
    alambique_ID = entry["_id"]
    # get tags
    tags = entry['data'].get('tags')
    # put tags in entry in pretoolsDev {'source' : [ID]}
    if tags:
        try:
            # ----- update pretoolsDev ------

            query = {
                "source.id": alambique_ID
            }
            pretools_entry = mongo_adapter.fetch_entry("pretoolsDev", query)
            if not pretools_entry:
                print(f"Entry not found pretoolsDev for ID: {alambique_ID}")
                continue
        
            n_pretools += 1
            mongo_adapter.update_entry("pretoolsDev", pretools_entry["_id"], {"data.tags": tags})

            # ----- update toolsDev ------
            query = {
                "source": pretools_entry["_id"]
            }
            tools_entry = mongo_adapter.fetch_entry("toolsDev", query)
            if not tools_entry:
                print(f"Entry not found in toolsDev for ID: {pretools_entry['_id']}")
                continue

            n_tools += 1
            mongo_adapter.update_entry("toolsDev", tools_entry["_id"], {"data.tags": tags})

        except Exception:
            raise

print('---------------------- Summary -------------------------')
print(f"Total biotools entries in alambiqueDev processed: {n}")
print(f"Total pretoolsDev entries updated: {n_pretools}")
print(f"Total toolsDev entries updated: {n_tools}")