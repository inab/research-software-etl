import argparse
import json
from matplotlib.font_manager import findfont
import requests
import os
import logging


from utils import get_url, connect_db, push_entry, save_entry
from dotenv import load_dotenv


session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit 537.36 (KHTML, like Gecko) Chrome",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


def get_source(id_):
    string = id_.split('/')[5]
    source = string.split(':')[0]
    return(source)

def get_bioconda_biotools_galaxy_tools(tool):
    if tool['@id'].count('/')>5:
        source = get_source(tool['@id'])
        if source == 'biotools':
            tool['@data_source'] = 'biotools'
        elif source == 'bioconda':
            tool['@data_source'] = 'bioconda'
        elif source == 'galaxy':
            tool['@data_source'] = 'galaxy'

        tool['@source_url'] = tool['@id']
    else:
        logging.info(f'canonical_tool {tool["name"]}')

    return(tool)


def import_data():
    # 0.1 Set up logging
    parser = argparse.ArgumentParser(
        description="Importer of OpenEBench tools from OpenEBench Tool API"
    )

    parser.add_argument(
        "--env-file", "-e",
        help=("File containing environment variables to be set before running "),
        default=".env",
    ) 

    parser.add_argument(
        "--loglevel", "-l",
        help=("Set the logging level"),
        default="INFO",
    )
    parser.add_argument(
        "--logdir", "-d",
        help=("Set the logging directory"),
        default="./logs/summary.log",
    )
    args = parser.parse_args()
    numeric_level = getattr(logging, args.loglevel.upper())
    logs_dir = args.logdir

    logging.basicConfig(level=numeric_level, format='%(asctime)s - %(levelname)s - opeb_tools - %(message)s', filename=f'{logs_dir}', filemode='w')

    # 0.2 Load .env
    load_dotenv(args.env_file)


    # 1. connect database/set output file
    logging.info('Connecting to database')
    STORAGE_MODE = os.getenv('STORAGE_MODE', 'db')

    if STORAGE_MODE =='db':
        alambique = connect_db()

    else:
        OUTPUT_PATH = os.getenv('OUTPUT_PATH', './data/opebtools.json')


    # 2. Download all opeb
    logging.info('Downloading OPEB tools')
    URL_OPEB_TOOLS = os.getenv('URL_OPEB_TOOLS', 'https://openebench.bsc.es/monitor/tool')
    logging.info(f'OpenEBench tools URL: {URL_OPEB_TOOLS}')
    
    tools = get_url(URL_OPEB_TOOLS)
    if tools:
    
        logging.info('Tools obtained')
        # 3. Get tools
        logging.info(f'Processing {len(tools)} tools ...')
        #For tool in OPEB Tool db
        for tool in tools:       
            # 4. Process metadata
            tool = get_bioconda_biotools_galaxy_tools(tool)

            # 5. push to db/file
            if STORAGE_MODE=='db':
                push_entry(tool, alambique)

            else:
                save_entry(tool, OUTPUT_PATH)
        
        logging.info("end_importation")

    else:
        logging.error('error - crucial_object_empty')
        logging.error('No content to process. Exiting...')
        logging.info("end_importation")
        exit(1)


if __name__ == '__main__':
    import_data()