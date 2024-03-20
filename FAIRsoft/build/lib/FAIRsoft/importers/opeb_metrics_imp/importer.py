import requests as re
import json
import configparser
import os
import pymongo
from pymongo import MongoClient

import FAIRsoft
from FAIRsoft import utils

def getURLcontent(url):
    try:
        res = re.get(url)

    except:
        print("Data from OPEB download failed")
        return(None)

    else:
        return(res)

def add_source(entry):
    entry['@data_source'] = 'opeb_metrics' 
    return(entry)

def update_entries(entries):
    for i in range(len(entries)):
        entries[i] = add_source(entries[i])

    return(entries) 

def save_JSON(response, out_filename):
    # 2 steps: decoding and writing
    # we could use only one json.dump()
    with open(out_filename, 'w') as outfile:
        try:
            content_decoded=json.loads(response.text) 
        except:
            print("Could not decode opeb db JSON")
        else:
            entries = update_entries(content_decoded)
            json.dump(entries, outfile)

def push_to_DB(response, collection):
    # 2 steps: decoding and writing
    # we could use only one json.dump()
    try:
        content_decoded=json.loads(response.text) 
    except:
        print("Could not decode opeb db JSON")
    else:
        entries = update_entries(content_decoded)
        collection.insert_many(entries)
    return

def parse_config(configfile):
    config = configparser.ConfigParser()
    config.read(configfile)
    params = {
        'metrics_url': config['URLS']['METRICS'],
        'output_dir' : config['PATHS']['OUTDIR']
    }
    return(params)

def import_data():
    # 1. connect to DB/get output files
    STORAGE_MODE = os.getenv('STORAGE_MODE', 'db')

    if STORAGE_MODE =='db':
        ALAMBIQUE = os.getenv('ALAMBIQUE', 'alambique') 
        client = MongoClient('localhost', 27017)
        alambique = client['observatory2'][ALAMBIQUE]

    else:
        OUTPUT_PATH = os.getenv('OUTPUT_PATH', './')
        OUTPUT_OPEB_TOOLS = os.getenv('OUTPUT_OPEB_TOOLS', 'opeb_tools.json') 
        output_file = OUTPUT_PATH + '/' + ALAMBIQUE + '/' + OUTPUT_OPEB_TOOLS


    # 2. Get metrics metadata from OPEB
    URL_OPEB_METRICS = os.getenv('URL_OPEB_METRICS', 'https://openebench.bsc.es/monitor/metrics/')
    json_res = getURLcontent(URL_OPEB_METRICS)
    
    # Decode response
    try:
        content_decoded=json.loads(json_res.text)
    except:
        raise Exception(f'Could not decode opeb metrics JSON. Please, check URL: {URL_OPEB_METRICS}')
    else:
        entries = update_entries(content_decoded)
        log = {'names':[],
           'n_ok':0,
           'errors': []}
        # output tools metadata
        for inst_dict in entries:
            if STORAGE_MODE=='db':
                print('pushing to db')
                try:
                    updateResult = alambique.update_many({'@id':inst_dict['@id']}, { '$set': inst_dict }, upsert=True)
                except Exception as e:
                    log['errors'].append({'file':inst_dict,'error':e})
                    return(log)
                else:
                    log['n_ok'] += 1
            else:
                log = FAIRsoft.utils.save_entry(inst_dict, output_file, log)

if __name__ == "__main__":
    import_data()