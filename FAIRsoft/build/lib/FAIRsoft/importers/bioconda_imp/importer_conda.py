####
# Old, not used anymore
####
import subprocess
import yaml
import json
import re
import sys
import os
from FAIRsoft import utils
import FAIRsoft  

def build_id(tool):
    id_template = "https://openebench.bsc.es/monitor/tool/bioconda_recipes:{name}:{version}/{type}"
    name = tool['name']
    version = tool.get('version')
    type_=''
    id_ = id_template.format(name=tool['name'], version=version, type=None)
    return(id_)

def retrieve_packages_metadata():
    command = 'conda search -i -c bioconda'
    print('Running command "conda search -i -c bioconda" to get all bioconda packages')
    process = subprocess.check_output(command, shell=True)
    output = str(process)
   
    STORAGE_MODE = os.getenv('STORAGE_MODE', 'db')
    ALAMBIQUE = os.getenv('ALAMBIQUE', 'alambique') 

    if STORAGE_MODE =='db':
        alambique = FAIRsoft.utils.connect_collection(ALAMBIQUE)
    else:
        OUTPUT_PATH = os.getenv('OUTPUT_PATH', './')
        OUTPUT_BIOCONDA_CONDA = os.getenv('OUTPUT_BIOCONDA_CONDA', 'bioconda_conda.json') 
        output_file = OUTPUT_PATH + '/' + ALAMBIQUE + '/' + OUTPUT_BIOCONDA_CONDA

    instances = re.split(r'--[-]*', output)
    log = {'tools':0,
            'n_ok':0,
            'errors': []}
    print('Parsing results...')

    for inst in instances[:10]:
        file_ = ''
        fields = inst.split('\\n')
        for field in fields[1:]:
            field.lstrip
            field = field.replace('::','')
            if ':' in field or '- ' in field:
                file_ = file_ + '\n' + field
        try:
            inst_dict = yaml.safe_load(file_)
        except Exception as e:
            log['errors'].append({'file':file_,'error':e})            
        else:
            if inst_dict:
                if 'conda.anaconda.org/bioconda/' in inst_dict['url']:
                    # 3. Generate id
                    inst_dict['@id'] = build_id(inst_dict)      
                    inst_dict['@data_source'] = 'bioconda_conda'
                    # output to collection/file
                    if STORAGE_MODE=='db':
                        log = FAIRsoft.utils.push_entry(inst_dict, alambique, log)
                    else:
                        log = FAIRsoft.utils.save_entry(inst_dict, output_file, log)

                else:
                    log['errors'].append({'file':file_,'error':'Empty inst_dict'})
            else:
                log['errors'].append({'file':file_,'error':'Empty inst_dict'}) 

        finally:
            log['tools'] += 1
                    
        # Keeping track of progress
        print(f"{log['tools']} packages processes --- {log['n_ok']} parsed and loaded sucessfully --- {len(log['errors'])} failed", end="\r", flush=True)
        #print(log)
    
    # Importation finished
    print(f'''\n----- Importation finished ----- \n Number of packages in Bioconda {log['tools']}''')
    print('Exceptions\n')
    for e in log['errors']:
        print(e['error'])
    
    return
    
if __name__=='__main__':
    # retrieve metadata
    retrieve_packages_metadata()

