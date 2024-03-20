import os
import importlib
import logging 

import FAIRsoft
import FAIRsoft.utils
from FAIRsoft.transformation.meta_transformers import tool_generators


def get_raw_data_db(source, alambique):
    logging.debug(f"Extracting raw data of source {source} from collection {alambique.name}")
    raw = alambique.find({"@data_source":source})
    return list(raw)

   
def output_bioconda_dict(generator, source):
    if source == 'bioconda_recipes':
        generator.type_dictionary('bioconda_types.json')


def open_raw_files(source):
    import json
    files_sources = {
        'BIOCONDUCTOR':'OUTPUT_BIOCONDUCTOR',
        'BIOCONDA':'OUTPUT_OPEB_TOOLS',
        'BIOTOOLS':'OUTPUT_OPEB_TOOLS',
        'TOOLSHED':'OUTPUT_TOOLSHED',
        'GALAXY_METADATA':'OUTPUT_TOOLSHED',
        'SOURCEFORGE':'OUTPUT_SOURCEFORGE',
        'GALAXY_EU': 'OUTPUT_OPEB_TOOLS',
        'OPEB_METRICS': 'OUTPUT_OPEB_METRICS',
        'BIOCONDA_RECIPES':'OUTPUT_BIOCONDA_RECIPES',
        'BIOCONDA_CONDA':'OUTPUT_BIOCONDA_CONDA',
        'REPOSITORIES': 'OUTPUT_REPOS',
    }
    try:
        OUTPUT_PATH = os.getenv('OUTPUT_PATH', './data')
        data_file = OUTPUT_PATH    + '/' + os.getenv(files_sources[source])
    except KeyError:
        print("No file for {}".format(source))
        raise
    except TypeError:
        print("No file for {}".format(files_sources[source]))
        raise
    else:
        with open(data_file, 'r') as infile:
            raw = json.load(infile)

        logging.info(f"Extracted raw data from {data_file}")
        logging.info(f"{len(raw)} entries from {files_sources[source]}")

        return raw


def add_to_pretools_file(insts, output_file):
    import json
    if not os.path.isfile(output_file):
            with open(output_file, 'w') as outfile:
                json.dump(insts, outfile)
    else:   
        with open(output_file) as json_data_file:
            pretools = json.load(json_data_file)
        pretools.append(insts)


def transform_this_source(raw, this_source_label):
    # Instantiate toolGenerator specific to this source
    logging.debug(f"Instantiating toolGenerator for {this_source_label}")
    generator_module = importlib.import_module(f".meta_transformers", 'FAIRsoft.transformation')
    
    logging.debug(f"Transforming raw data into instances")
    generator = generator_module.tool_generators[this_source_label](raw)
    
    # Export types dictionary in case of bioconda raw data 
    output_bioconda_dict(generator, this_source_label)
    
    # From instance objects to dictionaries
    insts = [i.__dict__ for i in generator.instSet.instances]
    logging.debug(f"Transformed {len(insts)} instances")
    return(insts)


def transform(loglevel, **kwargs):

    logging.basicConfig(level=loglevel)
    logging.getLogger('bibtexparser').setLevel(logging.WARNING)

    # Set environment variables:
    HOST = os.getenv('HOST', 'localhost')
    PORT = os.getenv('PORT', 27017)
    DB = os.getenv('DB', 'test')
    ALAMBIQUE = os.getenv('ALAMBIQUE', 'alambique')
    PRETOOLS = os.getenv('PRETOOLS', 'pretools') 

    STORAGE_MODE = os.getenv('STORAGE_MODE', 'db')
    if STORAGE_MODE =='db':
        logging.info('Storage mode: `database`')
        # raw data (input) collection
        logging.debug(f'Connecting to raw data collection {ALAMBIQUE} in database {DB}. Host: {HOST}:{PORT}')
        alambique = FAIRsoft.utils.connect_collection(host=HOST, port=int(PORT), db=DB, collection=ALAMBIQUE)
        # transformed data collection
        logging.debug(f'Connecting to raw data collection {PRETOOLS} in database {DB}. Host: {HOST}:{PORT}')
        pretools = FAIRsoft.utils.connect_collection(host=HOST, port=int(PORT), db=DB, collection=PRETOOLS)

    else:
        # Path of output file where the transformed data will be stored
        logging.info('Storage mode: `file`')
        logging.debug(f'Output file: {PRETOOLS}.json')
        output_file = os.getenv('OUTPUT_PATH', './') + '/' + PRETOOLS + '.json'

    # Run whole transformation pipeline
    for source in FAIRsoft.utils.sources_to_transform:
        logging.debug('Next source: {}'.format(source))

        # Check if source has to be transformed
        if os.getenv(source) == 'True':
            # label to match "source" field in the raw data and appropriate transformer
            this_source_label = FAIRsoft.utils.sources_labels[source]
                        
            # 1. getting raw data
            logging.info(f"------------- {source} -------------")
            logging.debug(f"Accessing data from `{source}` in database")
            if STORAGE_MODE =='db':
                raw_data = get_raw_data_db(this_source_label, alambique)
            else:
                raw_data = open_raw_files(source)
            
            if not raw_data:
                logging.info(f"No entries found for {this_source_label}")
            else:
                # 2. transformation
                logging.info(f"Transforming raw tools metadata from {this_source_label}")
                insts = transform_this_source(raw_data, this_source_label)
                
                # 3. output transformed data
                if STORAGE_MODE =='db':
                    log = {'errors':[], 'n_ok':0, 'n_err':0, 'n_total':len(insts)}
                    logging.debug("Updating database")
                    n=0
                    landmarks = {str(int((len(insts)/10)*i)): f"{i*10}%" for i in range(0,11)}
                    for inst in insts:
                        if str(n) in landmarks.keys():
                            logging.debug(f'{n}/{len(insts)} ({landmarks[str(n)]}) instances pushed to database\r')

                        inst['@id'] = f"https://openebench.bsc.es/monitor/tool/{inst['source'][0]}:{inst['name']}:{inst['version'][0]}/{inst['type']}"
                        log = FAIRsoft.utils.update_entry(inst, pretools, log)
                        #log = FAIRsoft.utils.push_entry(inst, pretools, log)
                        n+=1
                    
                    logging.info(f"Pushed {log['n_ok']} entries to database")
           
                else:
                    add_to_pretools_file(insts, output_file)    
                    logging.info(f"Saved to file")
        else:
            logging.info(f"Skipping {source}")
            

if __name__ == "__main__":
    
    transform()