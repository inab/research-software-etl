from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter

positive_tests = set()
N = 0
for record in mongo_adapter.fetch_entries("pretoolsDev", {'data.source':'toolshed'}):
    N += 1
    # fetch original alambique record
    original = record['source'][0]
    original = mongo_adapter.fetch_entry("alambiqueDev", {"_id": original['id']})
    test = original['data']['tests']
    if test:
        positive_tests.add(record['_id'])

    #mongo_adapter.update_entry("pretoolsDev", record['_id'], {'data.test' : test})


print(f"Positive tests: {len(positive_tests)} / {N} ({len(positive_tests)/N*100:.2f}%)")

N_positive = 0
N_total = 0
for record in mongo_adapter.fetch_entries("toolsDev", {'data.source':'toolshed'}):
    N_total += 1
    for original in record['source']:
        if original in positive_tests:
            mongo_adapter.update_entry("toolsDev", record['_id'], {'data.test' : True})
            N_positive += 1
            break

print(f"Positive tests in tools: {N_positive} / {N_total} ({N_positive/N_total*100:.2f}%)")
        
