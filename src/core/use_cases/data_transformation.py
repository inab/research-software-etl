import os
import importlib
import logging 
from typing import List, Dict

import src.core.domain.services.transformation.biotools_opeb


tool_generators = {
        'biotools' : src.core.domain.services.transformation.biotools_opeb.biotoolsOPEBToolsGenerator
}

def get_raw_data_db(source: str) -> List[Dict]:
    '''
    Connects to mongo database and returns raw data from a specific source.
    - source: label of the source to be transformed
    '''
    ALAMBIQUE = os.getenv('ALAMBIQUE', 'alambique')
    alambique = src.core.shared.utils.connect_collection(collection=ALAMBIQUE)
    
    logging.debug(f"Extracting raw data of source {source} from collection {alambique.name}")
    raw = alambique.find({ "@data_source" : source })
    
    return list(raw)


def transform_this_source(raw: Dict, this_source_label: str) -> List[Dict]:
    '''
    Transforms raw data from one specific source into instances.
    - raw: list of dictionaries with the raw data
    - this_source_label: label of the source to be transformed
    '''
    # Instantiate toolGenerator specific to this source
    logging.debug(f"Instantiating toolGenerator for {this_source_label}")
    
    #generator_module = importlib.import_module(f".meta_transformers", 'FAIRsoft.transformation')
    
    logging.debug(f"Transforming raw data into instances")
    generator = tool_generators[this_source_label](raw)
    
    # From instance objects to dictionaries
    insts = [i.__dict__ for i in generator.instSet.instances]
    logging.debug(f"Transformed {len(insts)} instances")
    return(insts)


def transform(loglevel, **kwargs):

    logging.basicConfig(level=loglevel)
    logging.getLogger('bibtexparser').setLevel(logging.WARNING)

    # transformed data collection
    PRETOOLS = os.getenv('PRETOOLS', 'pretools') 
    pretools = src.core.shared.utils.connect_collection(collection=PRETOOLS)

    # Run whole transformation pipeline
    for source in src.core.shared.utils.utils.sources_labels.keys():

        # Check if source has to be transformed
        if os.getenv(source) == 'True':
            # label to match "source" field in the raw data and appropriate transformer
            this_source_label = src.core.shared.utils.sources_labels[source]
                        
            # 1. getting raw data
            logging.info(f"------------ Starting transformation of data from {source} -------------")
            logging.debug(f"Accessing data from `{source}` in database")
            
            raw_data = get_raw_data_db(this_source_label)
            
            if not raw_data:
                logging.info(f"No entries found for {this_source_label}")
            else:
                # 2. transformation
                logging.info(f"Transforming raw tools metadata from {this_source_label}")
                insts = transform_this_source(raw_data, this_source_label)
                
                # 3. output transformed data

                log = {'errors':[], 'n_ok':0, 'n_err':0, 'n_total':len(insts)}
                logging.debug("Updating database")
                n=0
                landmarks = {str(int((len(insts)/10)*i)): f"{i*10}%" for i in range(0,11)}
                for inst in insts:
                    if str(n) in landmarks.keys():
                        logging.debug(f'{n}/{len(insts)} ({landmarks[str(n)]}) instances pushed to database\r')

                    identifier = inst['name']
                    log = src.core.domain.utils.update_entry(inst, pretools, log)
                    
                    n+=1
                
                    logging.info(f"Pushed {log['n_ok']} entries to database")

        else:
            logging.info(f"Skipping {source}")
            

if __name__ == "__main__":
    
    transform()