 # This is an example of the whole integration process.


import pymongo
import os
import logging
from bson import json_util


from src.application.services.integration.entries_recovery import recover_shared_name_link
from src.application.services.integration.conflict_detection import detect_conflicts
from src.application.services.integration.disambiguation import disambiguate_entries
from src.application.services.integration.group_entries import group_by_key_with_links



# =========================
# 1. Initialize MongoDB Client
# =========================
def initialize_client():
    """Initialize MongoDB Client"""
    mongo_host = os.getenv('MONGO_HOST', 'localhost')
    mongo_port = os.getenv('MONGO_PORT', '27017')
    mongo_user = os.getenv('MONGO_USER')
    mongo_pass = os.getenv('MONGO_PWD')
    mongo_auth_src = os.getenv('MONGO_AUTH_SRC', 'admin')

    logging.info(f"Connecting to MongoDB at {mongo_host}:{mongo_port}")

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



if __name__ == "__main__":


    # This should be done using the adapters devised for this purpose 
    client = initialize_client()
    db = client['oeb-research-software']
    entries = list(db.pretoolsDev.find())


    # =========================
    #  Group All Entries
    # =========================
    grouped_by_key = group_by_key_with_links(entries)

    grouped_entries_file = "data/grouped.json"
    with open(grouped_entries_file, 'w') as f:
        s = json_util.dumps(grouped_by_key)
        f.write(s)

    # =========================
    # Recover groups of shared name and non-repository link 
    # =========================
    grouped_instances = recover_shared_name_link(grouped_by_key)


    # =========================
    # Conflict detection
    # =========================
    disconnected_entries_file = "data/disconnected_entries.json"
    instances_dictionary_file = "data/instances_dict.json"

    detect_conflicts(grouped_entries_file, disconnected_entries_file)


    # =========================
    # Disambiguate
    # =========================

    disambiguated_grouped = disambiguate_entries(disconnected_entries_file, instances_dictionary_file, grouped_entries_file)


    # =========================
    # prepare final output for merging
    # =========================
    final_instances_groups = [group['instances'] for group in disambiguated_grouped.values()]

    with open('data/data.json', 'w') as f:
        s = json_util.dumps(final_instances_groups)
        f.write(s)

    print("Integration complete. Results saved to 'data.json'.")

