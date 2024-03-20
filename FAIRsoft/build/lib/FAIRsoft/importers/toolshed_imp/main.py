import json
import os
import logging
import argparse
from dotenv import load_dotenv

from repos_metadata_importer import reposFetcher
from galaxy_metadata import dMetadataFetcher

from repos_config_importer import toolShedMetadataFetcher


def import_data(only_new):
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
    print(f"Logging level: {numeric_level}")
    print(f"Logging directory: {logs_dir}")

    logging.basicConfig(level=numeric_level, format='%(asctime)s - %(levelname)s - toolshed - %(message)s', filename=f'{logs_dir}', filemode='w')
    logging.getLogger('urllib3').setLevel(logging.INFO)


    # 0.2 Load .env
    load_dotenv(args.env_file)

    logging.info("start_importation")

    #1. Fetch galaxy metadata
    logging.debug('Initializing reposFetcher object to fetch metadata from the Galaxy Toolshed')
    RF = reposFetcher()

    logging.debug('Fetching raw metadata of all the repositories from the Galaxy Toolshed.')
    RF.fetch_tools()

    repositories_metadata = RF.all_metadatas
    GALAXY_METADATA=os.getenv('GALAXY_METADATA', './data/galaxy_metadata.json')

    logging.debug(f'Exporting raw metadata to file: {GALAXY_METADATA}...')
    RF.export_metadatas(GALAXY_METADATA)
    #2. Parse and push fetched metadata to database/file
    ## Only for testing
    #with open(GALAXY_METADATA, 'r') as meta_file:
    #    repositories_metadata = json.load(meta_file)
    
    logging.info('Parsing and saving Galaxy Toolshed Repositories Metadata...')
    dMFetcher = dMetadataFetcher(repositories_metadata) ## --- testing  here
    dMFetcher.process_metadata()
    
    #4. Download and process configuration files in repos
    logging.debug('Initializing toolShedMetadataFetcher object to fetch metadata from the Galaxy Toolshed')
    toolShedMDF = toolShedMetadataFetcher(tools_galaxy_metadata = repositories_metadata, 
                                          only_new=only_new)
    
    logging.debug('Getting repositories zips and processing.')
    toolShedMDF.get_toolShed_files()

    logging.info("end_importation")


if __name__ == '__main__':
    import_data(False)