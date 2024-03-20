import json
from pymongo import MongoClient


def add_source(entry):
    entry['@data_source'] = 'opeb_metrics' 
    return(entry)

def update_entries(entries):
    for i in range(len(entries)):
        entries[i] = add_source(entries[i])
    return(entries)

def push_to_DB(metrics):
    for entry in metrics:
        entry['@data_source'] = 'opeb_metrics' 
        updateResult = alambique.update({'@id':entry['@id']}, { '$set': entry }, upsert=True, multi=True)
    return

client = MongoClient(port=27017)
db = client.OPEB
alambique = db.alambique
path='/home/eva/FAIRsoft/FAIRsoft_ETL/tools_importers/data/metrics.json'

with open(path, 'r') as input: 
    try:
        metrics = json.load(input)
    except Exception as e:
        raise(e)
    else:
        push_to_DB(metrics)
