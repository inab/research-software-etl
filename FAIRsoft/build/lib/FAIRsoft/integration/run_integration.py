from modulefinder import STORE_GLOBAL
import sys
import time
import pickle
import os
import logging

import json
from pymongo import MongoClient
from munch import munchify

from FAIRsoft.integration.integration import build_pre_integration_dict
from FAIRsoft.integration.integration import create_integrated_instances

from FAIRsoft.utils import timeit
from FAIRsoft.utils import instance
from FAIRsoft.utils import sources_labels
from FAIRsoft.utils import sources_to_transform
from FAIRsoft.utils import connect_collection


def open_json_collection(file_name: str):
    """Opens a JSON file
    
    file_name: path to the JSON file
    Used to open <pretools.json>  and <tools.json>
    """
    with open(file_name, 'r') as f:
        data = json.load(f)
        return(data)


def collect_pretools_instances(pretools, STORAGE_MODE):
    """Collects all the instances in pretools from the sources specified in configuration (.env)

    pretools: either a 'pymongo.collection.Collection' or a list of dictionaries
    """

    sources = sources_to_transform

    allInsts = []
    N_instances = 0

    for source in sources:
        if os.getenv(source, 'True') == 'True':
            logging.info("Collecting instances from %s"%(source))
            this_source_label = sources_labels[source]

            # Dependign on the storage_mode (db/file), get instances apply appropriate method to get data
            if STORAGE_MODE=='db':
                insts_iter = pretools.find({'source': this_source_label})
            else:
                insts_iter = [tool_dict for tool_dict in pretools if tool_dict['source'] == [this_source_label]]

            # turn to instance object
            insts = [instance(dictionary = inst) for inst in insts_iter]
            
            allInsts.append(insts)
            names=set([inst.name for inst in insts])
            N_instances += len(insts)
            
            logging.info(f"Entries from {this_source_label}: {len(insts)}")
            logging.info(f"Generic tools from {this_source_label}: {len(names)}")

    logging.info(f"Total instances:{N_instances}")    
    return(allInsts)

def open_pickle(filename):
    with open(filename, 'rb') as f:
        x = pickle.load(f)
        return(x)

def save_to_json(item, filename):
    with open(filename, 'w') as fp:
        json.dump(item, fp)

def save_names_to_file(totalNames, filename):
    with open(filename, 'w') as outfile:
        for name in totalNames:
            outfile.write("%s\n"%(name))

def save_insts_by_name(inst_name_dict, filename):
    """Saves a dictionary with key=tool name and value=list(instances of that tool)
    
    inst_name_dict is a dictionary of instances by tool name. 
    # {name_1: [instance1, instance2, ...], [instance1'], [instance1'', instance2'', ...], ...}
    """
    with open(filename, 'w') as fp:
        json.dump(inst_name_dict, fp)
    
@timeit
def run_integration(loglevel=logging.INFO):
    logging.basicConfig(level=loglevel)

    HOST = os.getenv('HOST', 'localhost')
    PORT = os.getenv('PORT', 27017)
    DB = os.getenv('DB', 'observatory2')
    PRETOOLS = os.getenv('PRETOOLS', 'pretools') 
    TOOLS = os.getenv('TOOLS', 'tools') 

    STORAGE_MODE = os.getenv('STORAGE_MODE', 'db')
    if STORAGE_MODE == 'db':
        # un-integrated collection of instances (input instances)
        pretools = connect_collection(host=HOST, port=int(PORT), db=DB, collection=PRETOOLS)
        # integrated collection of instances (output instances)
        tools = connect_collection(host=HOST, port=int(PORT), db=DB, collection=TOOLS)
    else:
        pretools_file = os.getenv('OUTPUT_PATH', './') + '/' + PRETOOLS + '.json'
        pretools = open_json_collection(pretools_file)
        tools_file = os.getenv('OUTPUT_PATH', './') + '/' + TOOLS + '.json'
        tools = open_json_collection(tools_file)


    ######----------- Data restructuring and integration ------------------------------------##########

    # 1. Collecting instances from pretools
  
    allInsts = collect_pretools_instances(pretools, STORAGE_MODE)
    
    totalNames, pre_integration_dict = build_pre_integration_dict(allInsts)

    ## Saving pre_integration_dict and names. 
    ## This step is not necessary, but it is useful for debugging
    # save_to_json(pre_integration_dict.copy(), 'pre_integration_dict.json')
    # save_names_to_file(totalNames, 'totalNames.txt')


    # 2. Integration of "tool" instances of same ID (name, type)
    n = []
    for k in pre_integration_dict.keys():
        for kk in pre_integration_dict[k].keys():
            n.append(len(pre_integration_dict[k][kk]))

    # 3. Create integrated instances and push to db/output to file.
    result, log = create_integrated_instances(pre_integration_dict, tools, STORAGE_MODE)
 

if __name__ == '__main__':
    run_integration()
    