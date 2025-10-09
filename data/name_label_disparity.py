import pymongo
import logging 
import os


def initialize_client():
    """Initialize MongoDB Client"""
    mongo_host = os.getenv('MONGO_HOST', 'localhost')
    mongo_port = os.getenv('MONGO_PORT', '27017')
    mongo_user = os.getenv('MONGO_USER')
    mongo_pass = os.getenv('MONGO_PWD')
    mongo_auth_src = os.getenv('MONGO_AUTH_SRC', 'admin')

    logging.info(f"Connecting to MongoDB at {mongo_host}:{mongo_port}")

    # Initialize MongoDB Client with AutoReconnect handling
    try:
        client = pymongo.MongoClient(
            host=[f'{mongo_host}:{mongo_port}'],
            username=mongo_user,
            password=mongo_pass,
            authSource=mongo_auth_src,
            authMechanism='SCRAM-SHA-256',
            maxPoolSize=100,
            serverSelectionTimeoutMS=5000  # Avoid indefinite hanging
        )
        return client
    except Exception as e:
        logging.error(f"MongoDB connection failed: {e}")
        raise

mongo_client = initialize_client()
db = mongo_client['oeb-research-software']
collection = db['alambiqueDev']

cases = []
for doc in collection.find({}):
    if '@label' in doc['data']:
        label = doc['data']['@label']
        name = doc['data'].get('name')
        source = doc['@data_source']
        origin = doc['data']['@source_url']

        if label.lower() != name.lower():
            cases.append({
                'label': label,
                'name': name,
                'source': source,
                'origin': origin
            })

print(f"Total cases: {len(cases)}")

# distribution of sources 
sources = {}

for case in cases:
    source = case['source']
    if source not in sources:
        sources[source] = 0
    sources[source] += 1

print(sources)

# print first 10 cases
# write biotools cases to a file 

biotools_cases = []
for case in cases:
    if case['source'] == 'biotools':
        biotools_cases.append(case)

with open('biotools_cases.txt', 'w') as file:
    for case in biotools_cases:
        string = f"{case['label']} - {case['name']} - {case['origin']}"
        file.write(string)
        file.write('\n')

