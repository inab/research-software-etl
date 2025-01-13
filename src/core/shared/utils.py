from functools import wraps
import os
import time
import logging
from dotenv import load_dotenv
from datetime import datetime

# import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection

# --------------------------------------------
# Constants 
# --------------------------------------------
global webTypes
webTypes = ['rest', 'web', 'app', 'suite', 'workbench', 'db', 'soap', 'sparql']

# Labels of sources accross FAIRsoft pacakage. Must be consistent!!!! 
# Present in:
# 1.- 'sources' field in `instance`` objects (and anywhere they appear in code) 
# 2.- toolGenerators in FAIRsoft.meta_transformers
# if labels change in one place, they must change in the others for everythong to keep working

sources_labels = {
    'BIOCONDUCTOR':'bioconductor',
    'BIOCONDA':'bioconda',
    'BIOTOOLS':'biotools',
    'TOOLSHED':'toolshed',
    'GALAXY_METADATA':'galaxy_metadata',
    'SOURCEFORGE': 'sourceforge',
    'GALAXY_EU': 'galaxy',
    'OPEB_METRICS':'opeb_metrics',
    'BIOCONDA_RECIPES':'bioconda_recipes',
    'BIOCONDA_CONDA':'bioconda_conda',
    'REPOSITORIES': 'repository',
    'GITHUB': 'github',
    'BITBUCKET': 'bitbucket'
}

# --------------------------------------------
# Helper functions
# --------------------------------------------

def push_entry(tool:dict, collection: Collection):
    '''Push tool to collection.

    tool: dictionary. Must have at least an '@id' key.
    collection: collection where the tool will be pushed.
    log : {'errors':[], 'n_ok':0, 'n_err':0, 'n_total':len(insts)}
    '''    
    try:
        # if the entry already exists, update it
        if collection.find_one({"_id": tool['_id']}):
            update_entry(tool, collection)
        # if the entry does not exist, insert it
        else:
            inset_new_entry(tool, collection)
        
    except Exception as e:
        logging.warning(f"error - {type(e).__name__} - {e}")

    else:
        logging.info(f"pushed_to_db_ok - {tool['_id']}")
    finally:
        return
    

def update_entry(entry: dict, collection: Collection):
    '''Updates an entry in the collection.

    entry: dictionary. Must have at least an '_id' key.
    collection: collection where the entry will be updated.
    '''
    # Ensure '_id' exists in entry
    if '_id' not in entry:
        logging.error("Entry must contain an '_id' field.")
        return

    # Copy entry to avoid mutating the original dict
    update_document = entry.copy()

    # keep the original creation metadata if entry exists in the collection
    original_entry = collection.find_one({'_id': entry['_id']})
    if original_entry:
        update_document['@created_at'] = original_entry['@created_at']
        update_document['@created_by'] = original_entry['@created_by']
        update_document['@created_logs'] = original_entry['@created_logs']
                                         

    try:
        # Use replace_one instead of update_one for replacing the whole document
        # Make sure to set upsert=True if you want to insert a new document when no document matches the filter
        result = collection.replace_one({"_id": entry['_id']}, update_document, upsert=True)
        if result.matched_count > 0:
            logging.info(f"Document with _id {entry['_id']} updated successfully.")
        else:
            logging.info(f"No matching document found with _id {entry['_id']}. A new document has been inserted.")
    except Exception as e:
        logging.warning(f"Error updating document - {type(e).__name__} - {e}")

        
def inset_new_entry(entry: dict, collection: Collection):
    '''Inserts a new entry in the collection.

    entry: dictionary. Must have at least an '_id' key.
    collection: collection where the entry will be inserted.
    '''
    try:
        collection.insert_one(entry)
    except Exception as e:
        logging.warning(f"error - {type(e).__name__} - {e}")
    else:
        logging.info(f"inserted_to_db_ok - {entry['_id']}")
    finally:
        return


def connect_collection_local(collection_name: str):
    '''Connect to MongoDB and return the database and collection objects.

    '''
    # Connect to MongoDB
    mongoClient = MongoClient('localhost', 27017)
    db = mongoClient['oeb-research-software']
    alambique = db[collection_name]

    return alambique


def connect_collection(collection:str='test'):
    '''Returns the collection object for the given collection name. 
    This is a helper function for any code that needs to access a collection.

    collection_name: name of collection to access
    Port, host and database are specified in .env file.    
    '''
    # ------ PARAMETERS ------
    load_dotenv()
    mongoHost = os.getenv('MONGO_HOST', default='localhost')
    mongoPort = os.getenv('MONGO_PORT', default='27017')
    mongoUser = os.getenv('MONGO_USER')
    mongoPass = os.getenv('MONGO_PWD')
    mongoAuthSrc = os.getenv('MONGO_AUTH_SRC', default='admin')
    mongoDb = os.getenv('MONGO_DB', default='oeb-research-software')
    

    collections = {
        'pretools' : os.environ.get('PRETOOLS', default='pretoolsDev'),
        'alambique' : os.environ.get('ALAMBIQUE', default='alambiqueDev'),
        'tools' : os.environ.get('TOOLS', default='toolsDev'),
        'licensesMapping' : os.environ.get('LICENSES_COLLECTION', default='licensesMapping'),
    }

    if collections.get(collection): 
        collection = collections[collection]
    else:
        collection = collection

    logging.debug(f"Connecting to database {mongoDb} at {mongoHost}:{mongoPort}. Collection: {collection}.")

    # ------ CONNECTION ------
    if mongoUser and mongoPass:
        client = MongoClient(
                host=[f'{mongoHost}:{mongoPort}'],
                username=mongoUser,
                password=mongoPass,
                authSource=mongoAuthSrc,
                authMechanism='SCRAM-SHA-256'
            )
        collection = client[mongoDb][collection]
    else:
        collection = None

    return collection


def timeit(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f'Function {func.__name__}{args} {kwargs} Took {total_time:.4f} seconds')
        return result
    return timeit_wrapper


