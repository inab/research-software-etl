import os
import dotenv
import time 
import logging
import argparse

from dotenv import load_dotenv
from glob import glob

import ruamel.yaml
import bioconda_utils.recipe as brecipe # this module is installed in env 'bioconda'

from utils import push_entry, save_entry, connect_db


def get_tool_names(subdirectories):
    tool_names_subs_raw = []
    for directory in subdirectories:
        name = directory.split('/')[-2]
        tool_names_subs_raw.append(name)
    return(tool_names_subs_raw)

def retrieve_packages_metadata(tool, recipes_path):
    inst_dicts = extract_metadata(tool,recipes_path)
    
    if inst_dicts:
        for inst_dict in inst_dicts:
            if inst_dict:
                inst_dict['@id'] = build_id(inst_dict)  
                inst_dict['@data_source'] = 'bioconda_recipes'
          
    else:
        logging.warning(f"Error with {tool} - parsing")
        logging.warning('Empty inst_dict')

    return(inst_dicts)

def extract_metadata(package, recipes_path):
    insts = []
    try:
        recipe = brecipe.load_parallel_iter(recipes_path, package)
    except Exception as e:
        logging.warning(f"error with {package} - parsing")
        logging.warning(e)
        return(insts)
    else:
        for a in recipe:
            a.render
            a.meta['name'] = package
            if a.meta.get('package'):
                if a.meta['package'].get('name'):
                    a.meta['name']=a.meta['package']['name']
            
            insts.append(a.meta)
        
        return(insts)


def build_id(tool):
    id_template = "https://openebench.bsc.es/monitor/tool/bioconda_recipes:{name}:{version}/{type}"
    
    name = tool['package']['name']
    type_= list(get_type(tool))
    tool['type'] = type_

    id_ = id_template.format(name=name, version=None, type=type_)

    return(id_)

def get_type(tool):
    '''
    Tool type can be inferred from the recipe yaml file. 
    Decision tree to get the type of the tool:

    If test:
        If test.imports: 
            Lib
        If test.commands: 
            CMD
        If source_files:
            CMD
    Else:
        If build.entrypoints: 
            CMD
        Else-If (python OR perl OR r-base) in requirements.host:
            If (python OR perl OR r-base) in requirements.run:
                Lib
        Else:
            CMD
    '''

    type_ = set()
    type_ = check_tool_in_bioconductor(tool, type_)

    if tool.get('test'):
        type_ = check_tool_in_test(tool.get('test'), type_)
        
    else:
        if tool.get('build'):
            type_ = check_tool_in_build(tool.get('build'), type_)
            
        elif tool.get('requirements'):
            type_ = check_tool_host_target(tool.get('requirements'), type_)
            
    if len(type_) == 0:
        type_.add('cmd')

    return(type_)


def check_tool_in_bioconductor(tool, type_):
    '''
    If bioconductor in name and urls:
        Lib
    '''

    def check_bioc_in_name(tool_name):
        if 'bioconductor-' in tool_name:
            bioconductor = True
        else:
            bioconductor = False
        
        return(bioconductor)
    
    def check_bioc_in_source(tool_source, bioconductor):
        if tool_source:
            # source can be a list or a dict. The following handles it
            if isinstance(tool_source, ruamel.yaml.comments.CommentedMap):
                source = [tool_source]    
            elif isinstance(tool_source, ruamel.yaml.comments.CommentedSeq):
                source = tool_source
            else:
                source = []

            # source = list(s1, s2, ....)
            for l in source:
                if l.get('url'):
                    for url in l['url']:
                        if 'bioconductor' in url:
                            bioconductor = True
        
        return(bioconductor)

    def check_bioc_in_about(tool_about, bioconductor):
        if tool_about:
            if tool_about.get('home'):
                if 'bioconductor' in tool_about['home']:
                    bioconductor = True

        return(bioconductor)

    # Check if bioconductor in name, source and about
    bioconductor = check_bioc_in_name(tool.get('name'))
    bioconductor = check_bioc_in_source(tool.get('source'), bioconductor)
    bioconductor = check_bioc_in_about(tool.get('about'), bioconductor)
    
    if bioconductor == True:
        type_.add('lib')
    
    return(type_)

def check_tool_in_test(tool_test, type_):
    '''
    If test:
        If test.imports: 
            Lib
        If test.commands: 
            CMD
        If source_files:
            CMD
    '''
    if tool_test.get('commands'):
        if True not in ['$R' in command for command in tool_test['commands']]:
            type_.add('cmd')
    
    if tool_test.get('imports'):
        type_.add('lib')
    
    if tool_test.get('source_files'):
        type_.add('cmd')
    
    return(type_)

def check_tool_in_build(tool_build, type_):
    '''
    If build.entrypoints: 
            CMD
    '''
    if tool_build.get('entrypoints'):
        type_.add('cmd')
    return(type_)


def check_tool_host_target(tool_requirements, type_):
    '''
    Else-If (python OR perl OR r-base) in requirements.host:
            If (python OR perl OR r-base) in requirements.run:
                Lib
    '''
    if tool_requirements.get('host'):
        for host in tool_requirements['host']:
            if True in [lang in host for lang in ['r-base', 'python','perl'] ]:

                if tool_requirements.get('run'):
                    for run in tool_requirements.get('run'):
                        if True in [lang in run for lang in ['r-base', 'python','perl'] ]:
                            type_.add('lib')

    return(type_)


def process_recipes():
    # 0.1 Set up logging
    parser = argparse.ArgumentParser(
        description="Importer of Bioconda recipes"
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

    logging.basicConfig(level=numeric_level, format='%(asctime)s - %(levelname)s - bioconda - %(message)s', filename=f'{logs_dir}', filemode='w')

    # 0.2 Load .env
    load_dotenv(args.env_file)

    logging.info("start_importation")

    # 1. connect to DB/ get output file
    STORAGE_MODE = os.getenv('STORAGE_MODE', 'db')

    if STORAGE_MODE =='db':
        alambique = connect_db()
        
    else:
        OUTPUT_PATH = os.getenv('OUTPUT_PATH', './data/bioconda.json')

    # 2. List tool names in the directory
    recipes_path = os.getenv('RECIPES_PATH', './bioconda-recipes/recipes')        
    if not recipes_path:
        logging.info('RECIPES_PATH environment variable not set. Exiting importation.')
        
    else:
        subdirectories = glob("%s/*/"%(recipes_path))
        logging.debug(f'subdirectories: {subdirectories}')
        tool_names_subs_raw = get_tool_names(subdirectories)
        
        logging.info('List of names obtained')
        logging.info('Number of tools: %s'%(len(tool_names_subs_raw)))
    
        # For each tool, extract metadata and push to DB/file
        logging.info('Processing metadata')

        for tool in tool_names_subs_raw:

            # 3. Process metadata
            inst_dicts = retrieve_packages_metadata(tool, recipes_path)
            for inst_dict in inst_dicts:
                
                # 4. Push metadata to DB/file
                if STORAGE_MODE=='db':
                    push_entry(inst_dict, alambique)

                else:
                    save_entry(inst_dict, OUTPUT_PATH)

    logging.info("end_importation")
    
    


if __name__=='__main__':
    # Extract and push metadata
    process_recipes()


