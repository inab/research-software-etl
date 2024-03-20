import requests as re
import json
import os
import logging
import argparse
from dotenv import load_dotenv
from utils import get_url, connect_db, push_entry, save_entry


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

    logging.basicConfig(level=numeric_level, format='%(asctime)s - %(levelname)s - opeb_metrics - %(message)s', filename=f'{logs_dir}', filemode='w')

    # 0.2 Load .env
    load_dotenv(args.env_file)

    # 1. connect to DB/get output files
    logging.info('connecting to database')
    STORAGE_MODE = os.getenv('STORAGE_MODE', 'db')

    if STORAGE_MODE =='db':
        alambique = connect_db()

    else:
        OUTPUT_PATH = os.getenv('OUTPUT_PATH', './data/opeb_tools.json')

    logging.info("start_importation")
    # 2. Get metrics metadata from OPEB
    logging.info('downloading OPEB metrics entries')
    URL_OPEB_METRICS = os.getenv('URL_OPEB_METRICS', 'https://openebench.bsc.es/monitor/metrics/')
    logging.info(f'openEBench metrics URL:{URL_OPEB_METRICS}')
    content_decoded = get_url(URL_OPEB_METRICS)

    if content_decoded:

        logging.info(f'Processing {len(content_decoded)} OPEB metrics entries')

        for inst_dict in content_decoded:

             # 3. Add data source to each entry
            inst_dict['@data_source'] = 'opeb_metrics'

            # 4. output/push to db tools metadata
            if STORAGE_MODE=='db':
                push_entry(inst_dict, alambique)
            else:
                save_entry(inst_dict, OUTPUT_PATH)

        logging.info("end_importation")

    else:
        logging.error('error - crucial_object_empty')
        logging.error('No content to process. Exiting...')
        logging.info("end_importation")
        exit(1)
    
if __name__ == "__main__":
    import_data()