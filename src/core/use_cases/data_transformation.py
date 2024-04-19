import os
import logging 
from typing import List, Dict

from src.core.domain.services.transformation.standardizers_factory import StandardizersFactory
from src.core.domain.services.transformation.metadata import create_new_metadata, update_existing_metadata
from src.core.domain.entities.metadata.pretools import Metadata
from src.infrastructure.db.mongo_adapter import MongoDBAdapter

def get_raw_data_db(source: str) -> List[Dict]:
    '''
    Connects to mongo database and returns raw data from a specific source.
    - source: label of the source to be transformed
    '''
    logging.debug(f"Accessing data of source {source} in db collection {alambique.name}")

    ALAMBIQUE = os.getenv('ALAMBIQUE', 'alambique')
    alambique = src.core.shared.utils.connect_collection(collection=ALAMBIQUE)
    
    raw = alambique.find({ "@data_source" : source })
    
    return list(raw)


def standardize_entry(raw: Dict, this_source_label: str) -> List[Dict]:
    '''
    Transforms a raw enrty data from one specific source into instances.
    - raw: list of dictionaries with the raw data
    - this_source_label: label of the source to be transformed
    '''
    standardizer = StandardizersFactory.get_standardizer(this_source_label)
    tools = standardizer.process_transformation(raw)
    
    return(tools)

def get_identifier(entry: Dict) -> str:
    '''
    Extracts the identifier from a raw entry.
    - entry: dictionary with the raw data
    '''
    identifier = entry.get('_id', None)
    if not identifier:
        logging.error(f"No identifier found for entry {entry}")
        return None
    return identifier

def generate_metadata(identifier: str, mongo_adapter: MongoDBAdapter):
    '''
    Generates metadata for the transformed data.
    '''

    entry_exists_db = mongo_adapter.check_metadata('pretools', {'_id': identifier} )
    if entry_exists_db:
        metadata = create_new_metadata(identifier, 'pretools')
    else:
        existing_metadata  = mongo_adapter.get_entry_metadata('pretools', {'_id': identifier})
        existing_metadata = Metadata(**existing_metadata)
        metadata = update_existing_metadata(identifier, 'pretools', existing_metadata)
    
    return metadata
    

sources = [
    'biotools',
    'bioconda',
    'bioconda_recipes',
    'bioconductor',
    'galaxy_metadata',
    'toolshed',
    'galaxy',
    'sourceforge',
    'opeb_metrics'
]


def transform(loglevel,  sources: List[str] = sources, **kwargs):

    logging.basicConfig(level=loglevel)
    logging.getLogger('bibtexparser').setLevel(logging.WARNING)
    
    # Run whole transformation pipeline
    for source in sources:
            logging.info(f"Starting transformation of data from {source}")            
            mongo_adapter = MongoDBAdapter()

            raw_data = get_raw_data_db(source)
    
            if not raw_data:
                logging.info(f"No entries found for {source}")
            else:
                logging.debug(f"Transforming raw tools metadata from {source}")

                for entry in raw_data:
                    identifier = get_identifier(entry)
                    if identifier: 
                        insts = standardize_entry(entry, source)
                        metadata = generate_metadata(identifier, mongo_adapter)

                        for inst in insts:
                            document = metadata.to_dict_for_db_insertion()
                            document['data'] = inst.__dict__

                            mongo_adapter.update_entry('pretools', identifier, document)


if __name__ == "__main__":
    
    transform()