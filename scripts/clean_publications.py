from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from pprint import pprint

unique_dois = set()
n= 0

for pub in mongo_adapter.fetch_entries("publicationsMetadataDev", {}):
    n += 1
    if pub['data'].get('doi'):
        unique_dois.add(pub['data']['doi'])
    else:
        continue

print(f"Total unique DOIs: {len(unique_dois)}")
print(f"Total records: {n}")

counts_ids = {}
for pub in mongo_adapter.fetch_entries("publicationsMetadataDev", {}):
    if pub['data'].get('doi'):
        doi = pub['data']['doi']
        if doi in counts_ids:
            counts_ids[doi].append(pub['_id'])
        else:
            counts_ids[doi] = [pub['_id']]
    else:
        continue

duplicates = 0
print('Deleting duplicates:')
for doi, ids in counts_ids.items():
    if len(ids) > 1:
        duplicates += 1
        print(f"DOI: {doi}")
        print(f"IDs: {ids}")
        for id in ids[1:]:
            print(f"ID: {id}")
            mongo_adapter.delete_entry("publicationsMetadataDev", id)


print(f"Total duplicates: {duplicates}")