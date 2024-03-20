import json
import os
import FAIRsoft
from FAIRsoft import utils

from .repos_metadata_importer import reposFetcher
from .galaxy_metadata import dMetadataFetcher
from .repos_config_importer import toolShedMetadataFetcher

def import_data(only_new):   

    #1. Fetch galaxy metadata
    print('Fetching Galaxy Toolshed Repositories Metadata...')
    RF = reposFetcher()
    RF.fetch_tools()
    repositories_metadata = RF.all_metadatas

    OUTPUT_PATH = os.getenv('OUTPUT_PATH', './')
    ALAMBIQUE = os.getenv('ALAMBIQUE', 'alambique')
    GALAXY_METADATA=os.getenv('GALAXY_METADATA', 'galaxy_metadatas.json')
    metadata_out=OUTPUT_PATH + '/' + ALAMBIQUE + '/' + GALAXY_METADATA

    RF.export_metadatas(metadata_out)
    
    #2. Parse and push fetched metadata
    print('Parsing Galaxy Toolshed Repositories Metadata...')
    with open(metadata_out, 'r') as meta_file:
        repositories_metadata = json.load(meta_file)
    
    dMFetcher = dMetadataFetcher(repositories_metadata)
    dMFetcher.process_metadata()
    
    #4. Download and process configuration files in repos
    print('Fetching Galaxy Toolshed Metadata inside repositories...')
    toolShedMDF = toolShedMetadataFetcher(tools_galaxy_metadata = repositories_metadata, 
                                          only_new=only_new)
    toolShedMDF.get_toolShed_files()


if __name__ == '__main__':
    import_data(False)