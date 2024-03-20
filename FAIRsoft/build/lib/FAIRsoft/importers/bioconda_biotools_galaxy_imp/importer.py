import argparse
import json
from matplotlib.font_manager import findfont
import requests
import ssl
import os
import pymongo
from pymongo import MongoClient
import FAIRsoft

from dotenv import load_dotenv

load_dotenv()


session = requests.Session()
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit 537.36 (KHTML, like Gecko) Chrome",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

def getHTML(url, verb=False):
    ssl._create_default_https_context = ssl._create_unverified_context
    try:
        req = session.get(url, headers=headers, timeout=(20, 50), verify=False)
        # req = urllib.request.urlopen(url)
    except Exception as e:
        print(e)
        print(e)
        return None
    else:
        return req

def get_source(id_):
    string = id_.split('/')[5]
    source = string.split(':')[0]
    return(source)

def get_bioconda_biotools_galaxy_tools(tool, log):
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
        log['canonical_N'] +=1

    return(tool, log)


def import_data():
    # 0. connect database/set output files
    STORAGE_MODE = os.getenv('STORAGE_MODE', 'db')

    if STORAGE_MODE =='db':
        ALAMBIQUE = os.getenv('ALAMBIQUE', 'alambique') 
        client = MongoClient('localhost', 27017)
        alambique = client['observatory2'][ALAMBIQUE]

    else:
        OUTPUT_PATH = os.getenv('OUTPUT_PATH', './')
        OUTPUT_OPEB_TOOLS = os.getenv('OUTPUT_OPEB_TOOLS', 'opeb_tools.json') 
        output_file = OUTPUT_PATH + '/' + ALAMBIQUE + '/' + OUTPUT_OPEB_TOOLS


    # 1. Download all opeb
    URL_OPEB_TOOLS = os.getenv('OPEB_URL', 'https://openebench.bsc.es/monitor/tool')
    print(f'OpenEBench tools URL: {URL_OPEB_TOOLS}')
    re = getHTML(URL_OPEB_TOOLS)

    # 2. Get tools
    tools = re.json()
    log = {'errors':[], 'n_ok':0, 'names': [],'canonical_N': 0}
    #For tool in OPEB Tool db
    print('tools obtained')
    for tool in tools:
        # 3. Process metadata
        tool, log = get_bioconda_biotools_galaxy_tools(tool,log)
        # 4. push to db/file
        if STORAGE_MODE=='db':
            print('pushing to db')
            if 'about' in tool.keys():
                tool['about'].pop('date', None)
            try:
                updateResult = alambique.update_many({'@id':tool['@id']}, { '$set': tool }, upsert=True)
            except Exception as e:
                log['errors'].append({'file':tool,'error':e})
                return(log)
            else:
                log['n_ok'] += 1


        else:
            log = FAIRsoft.utils.save_entry(tool, output_file, log)
     
    print(log)

    # Importation finished
    print(f'''\n----- OPEB Tools Importation finished -----
    Number of tools in OPEB {len(log['names'])}
    Number of canonical tools: {log['canonical_N']}''')
    print('Exceptions\n')
    for e in log['errors']:
        print(e['error'])


if __name__ == '__main__':
    import_data()