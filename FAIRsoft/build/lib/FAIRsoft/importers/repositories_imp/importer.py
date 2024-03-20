import subprocess
import json
import os
import FAIRsoft
from FAIRsoft import utils

from os import listdir
from os.path import isfile, join


def run_repoenricher(base_path, out_path):
    # build repoenricher.pl command
    '''from 'pubmed-github-bitbucket/opeb-enrichers/repoEnricher/README.md'
    perl repoEnricher.pl --config myConfig.ini --directory=output
    '''
    config_path = '/'.join([base_path, 'config.ini'])
    repoEnricher='/'.join([base_path, 'repoEnricher.pl'])
    command_template = "perl {repoEnricher} --config {config} --directory={output}"
    command = command_template.format(repoEnricher=repoEnricher, config=config_path, output=out_path)
    print(command)

    # run command
    process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()

    return


def build_id(original_id):
    #parsing original id
    
    fields = original_id.split('/')

    if len(fields)>6:
        name_plus = fields[5]
        main_fields = name_plus.split(':')
        name = main_fields[1]
        if len(main_fields)>2:
            version =  main_fields[2]
        else:
            version = None
        
        type_ = fields[6]
        # building new id
        if version:
            name_version=':'.join([name, version])
        else:
            name_version = name
    
        template = 'https://openebench.bsc.es/monitor/tool/repository:{name_version}/{type_}'
        new_id = template.format(name_version=name_version, type_=type_)
        return(new_id)
    
    else:
        name = fields[5]
        template = 'https://openebench.bsc.es/monitor/tool/repository:{name}'
        new_id = template.format(name=name)
        return(new_id)
  

def import_data():
    # 1. run_enricher
    REPOENRICHER_PATH=os.getenv('REPOENRICHER_PATH', None)
    if REPOENRICHER_PATH:
        REPOENRICHER_OUTPUT_PATH=os.getenv('REPOENRICHER_OUTPUT_PATH', None)

    if REPOENRICHER_OUTPUT_PATH:
        run_repoenricher(REPOENRICHER_PATH, REPOENRICHER_OUTPUT_PATH)

    # 2. take all files in output folder, put "@source" in each and push to alambique
    OUTPUT_REPOS=os.getenv('OUTPUT_REPOS', 'repositories.json')

    repos_out_files = ['/'.join([OUTPUT_REPOS,f]) for f in listdir(OUTPUT_REPOS) if isfile(join(OUTPUT_REPOS, f))]
    if '/'.join([OUTPUT_REPOS,'manifest.json']) in repos_out_files:
        repos_out_files.remove('/'.join([OUTPUT_REPOS,'manifest.json']))

    # 3. Connection to database
    STORAGE_MODE = os.getenv('STORAGE_MODE', 'db')
    ALAMBIQUE = os.getenv('ALAMBIQUE', 'alambique')

    if STORAGE_MODE =='db':
        alambique = FAIRsoft.utils.connect_collection(ALAMBIQUE)
    else:
        OUTPUT_PATH = os.getenv('OUTPUT_PATH', './')
        OUTPUT_REPOS = os.getenv('OUTPUT_REPOS', 'opeb_metrics.json')
        output_file = OUTPUT_PATH + '/' + ALAMBIQUE + '/' + OUTPUT_REPOS

    log = {'names':[],
       'n_ok':0,
       'errors': []}
    # For file in output_path
    for out_file in repos_out_files:
        with open(out_file, 'r') as repo_entry:
            repo_json = json.load(repo_entry)
            # 4. add @source
            try:
                repo_json['@data_source'] = 'repository'
            except:
                print(repo_json)
            finally:
                # 5. insert in collection
                repo_json['@id'] = build_id(repo_json['@id'])
                #print(repo_json)
                if STORAGE_MODE=='db':
                    log = FAIRsoft.utils.push_entry(repo_json, alambique, log)
                else:
                    log = FAIRsoft.utils.save_entry(repo_json, output_file, log)
                    
if __name__ == '__main__':
    import_data()
