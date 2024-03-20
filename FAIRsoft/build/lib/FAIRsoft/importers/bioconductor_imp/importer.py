import argparse
import json
import requests
import re
import subprocess
import bs4
import os

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

from .list_packages import fetch_all_packages
import FAIRsoft
from FAIRsoft import utils


def get_program_arguments(arguments_parser): 
    arguments = arguments_parser.parse_args()
    return(arguments)

def program_arguments_parser():
    parser = argparse.ArgumentParser(
            prog='',
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--opeb', dest='opeb', action='store_true', help='If tools for which metadata is retrieved are those in OPEB (enricher mode). Otherwise all tools in Bioconductor (putre importer option). Default: all.')
    parser.add_argument('-urls_file_path', required=False, help='''Path file containing the list of URLs to scrap for enricher mode.''')
    return(parser)

# initializing session
session = requests.Session()
headers = {"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_5) AppleWebKit 537.36 (KHTML, like Gecko) Chrome",
"Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"}

# the html retriever
def getHTML(url, verb=False):
    '''
    Takes and url as an input and returns the corresponding
    bs4 object
    '''
    from bs4.dammit import EncodingDetector
    try:
        re = session.get(url, headers=headers, timeout=(10, 30))
    except:
        print(r'Cannot access HTML')
        return(None)
    else:
        if re.status_code == 200:
            # dealing with encoding
            http_encoding = re.encoding if 'charset' in re.headers.get('content-type', '').lower() else None
            html_encoding = EncodingDetector.find_declared_encoding(re.content, is_html=True)
            encoding = html_encoding or http_encoding

            # generating BeautifulSoup object
            bsObj = BeautifulSoup(re.content, 'html5lib', from_encoding=encoding)

            if verb == True:
                print("The title of html is %s"%bsObj.title.getText())
            return(bsObj)
        else:
            return(None)


def preParsing(bs):
    '''
    This function return to parts of the bsObject.
    part 1: extended name, description, authors, maintainers and citation
    part 2: a dictionary with all fragments under a <h3>.
    '''
    Name = bs.find('h1').get_text()
    html1 = []
    html2 = {}
    htmlsub2 = []
    for tag in bs.find('h2').next_siblings:
        if tag.name == 'h3':
            name = tag.contents[0]
            break
        else:
            html1.append(tag)

    if bs.find('div', attrs={"class":"bioc_citation"}):
        citation = 1
    else:
        citation = 0

    # Getting second part
    for tag in bs.find('h3').next_siblings:
        if tag.name == 'h3':
            html2[name] = htmlsub2
            htmlsub2 = []
            name = tag.contents[0]
        else:
            htmlsub2.append(tag)
    html2[name] = htmlsub2
    return(Name, citation, html1, html2)

def getInsDocDetArch(part2):
    instRaw = part2.get('Installation', None)
    docRaw = part2.get('Documentation', None)
    detailsRaw = part2.get('Details', None)
    packRaw = part2.get('Package Archives', None)

    return(instRaw, docRaw, detailsRaw, packRaw)


def parsePart1(bs, items):
    ps = [p for p in bs if p.name == 'p' ]
    if 'Bioconductor version' in ps[0].contents[0]:
        items['description'] = ps[1].contents[0]
        Auth = [a for a in ps[2].contents[0].split(':')[1].split(',') ]
        if ' and ' in Auth[-1]:
            last_auth = Auth[-1].split('and')
            items['authors'] = Auth[:-1] + last_auth
        else:
            items['authors'] = Auth

        Mant = [a for a in ps[3].contents[0].split(':')[1].split(',') ]
        if ' and ' in Mant[-1]:
            last_mant = Mant[-1].split('and')
            items['mantainers'] = Mant[:-1] + last_mant
        else:
            items['mantainers'] = Mant

    else:
        print('Unknown structure of part1. Aborting the parsin...')
    return(items)


def existInstallation(bs, items):
    instr = [a for a in bs if a.name == 'pre']
    if len(instr)>0:
        items['Installation instructions'] = True
    else:
        items['Installation instructions'] = False

    return(items)


def parseDocumentation(bs, items):
    table = [a for a in bs if a.name == 'table']
    if len(table) > 1:
        print('error in documentation parsing, aborting...')
    else:
        table = table[0]

    items['documentation'] = {}

    for row in table.findAll('tr'):
        cells = [cell for cell in row.findAll('td')]
        if cells[0].find('a') or cells[1].find('a'):
            doc = str(cells[0].find('a'))
            script = str(cells[1].find('a'))
            field = cells[2].get_text()
            field = field.replace('.','_')
            items['documentation'][field] = [doc, script]
    return(items)


def parseDetails(bs, items):
    table = [a for a in bs if a.name == 'table']
    if len(table) > 1:
        print('error in details parsing, aborting...')
    else:
        table = table[0]

    for row in table.findAll('tr'):
        cells = [cell for cell in row.findAll('td')]
        if re.sub('\s+', '', cells[1].get_text() ) in ['', ' ']:
            items[cells[0].get_text()] = None
        else:
            items[cells[0].get_text()] = re.sub('\s+', '', cells[1].get_text() )

    return(items)

import re
def parseArchives(bs, items):
    table = [a for a in bs if a.name == 'table']
    if len(table) > 1:
        print('error in archives parsing, aborting...')
    else:
        table = table[0]

    for row in table.findAll('tr'):
        cells = [cell for cell in row.findAll('td')]
        if re.sub('\s+', '', cells[1].get_text() ) in ['', ' ']:
            items[cells[0].get_text()] = None
        else:
            items[cells[0].get_text()] = re.sub('\s+', '', cells[1].get_text() )

    return(items)

def parseInput(InputPath):
    '''
    This function takes the input file and builds a list of urls
    required: the input path. Line format in input file: <url>\t<name>\n
    returns: a lis of urls in the file
    '''
    urls_file = open(InputPath, 'r')
    urls = []
    counter = 1
    counter_valid = 0
    for line in urls_file:
        if len(line.split('\t')) != 2:
            print("Input file line %s skipped: impossible to parse, number of columns != 2."%(counter))
        else:
            url = line.split('\t')[0]
            if "galaxy" not in url and "github" not in url:
                urls.append(check_protocol(url))
                counter_valid += 1
        counter += 1
    print("Number of URLs to be analyzed: %s"%(counter_valid))
    if urls == []:
        print("No URLs to analyze")
        return(None)
    else:
        return(urls)


def parseInput(InputPath):
    '''
    This function takes the input file and builds a list of urls
    required: the input path. Line format in input file: <url>\t<name>\n
    returns: a lis of urls in the file
    '''
    urls_file = open(InputPath, 'r')
    urls = []
    counter = 1
    counter_valid = 0
    for line in urls_file:
        if len(line.split('\t')) != 2:
            print("Input file line %s skipped: impossible to parse, number of columns != 2."%(counter))
        else:
            url = line.split('\t')[0]
            match = re.search("^(https?:\/\/)?(www.)?bioconductor.org\/packages\/[A-Za-z0-9_.]{1,15}\/bioc\/html\/.*?$", url)
            if match:
                urls.append(check_protocol(url))
                counter_valid += 1
        counter += 1
    print("Number of URLs to be analyzed: %s"%(counter_valid))
    if urls == []:
        print("No URLs to analyze")
        return(None)
    else:
        return(urls)


def check_protocol(url):
    '''
    '''
    if re.match('^http', url) != None: # To be changed for proper regex (beginning of line)
        return(url)
    else:
        return('https://' + url)

def clean_fields(items):
    #Split lists
    list_fields = ['Depends on me', 'Suggests', 'Suggests Me', 'Depends']
    for field in list_fields:
        if field in items and items[field]:
            items[field] = items[field].split(',')
    # remove dots
    keys=tuple(items.keys())
    for key in keys:
        if '.' in key:
            items[key.replace('.', '_')] = items[key]
            items.pop(key, None)
    return(items)


def parse_citation(citation):
    with open('tmp_citation.txt', 'w') as file_name:
        file_name.write(citation)

    command = ["anystyle","--stdout","-f", "json","parse","tmp_citation.txt"]
    process = subprocess.run(args = command, stdout=subprocess.PIPE).stdout
    #parsed = ast.literal_eval(process.decode("utf-8"))
    parsed = json.loads(process.decode("utf-8"))
    if parsed:
        return(parsed[0])
    else:
        return([])

import ast
def get_publication(driver, url, items):
    driver.get(url)
    try:
        citation = driver.find_element_by_class_name('bioc_citation')
    except:
        citation = None
        link = None
    finally:
        try:
            link = citation.find_element_by_tag_name('a')
            link = link.get_attribute('href')
        except:
            link = None

    pub_cit = parse_citation(citation.text)
    pub = {"url":link, "citation": pub_cit}
    items["publication"] = pub
    return(items)

def retrieve_metadata(bs, url, driver):
    items = {}
    name, citation, part1, part2 = preParsing(bs)
    items['name'] = name
    items['citation'] = citation
    instRaw, docRaw, detailsRaw, packRaw = getInsDocDetArch(part2)
    items = parsePart1(part1, items)
    items = existInstallation(instRaw, items)
    items = parseDocumentation(docRaw, items)
    items = parseDetails(detailsRaw, items)
    items = parseArchives(packRaw, items)

    if items['URL'] != None:
        items['links'] = [url] + [items['URL']]
    else:
        items['links'] = [url]
    
    items = get_publication(driver, url, items)
    items = clean_fields(items)
    items['@data_source'] = 'bioconductor'
    items['@source_url'] = url
    items['@id'] = f"https://openebench.bsc.es/monitor/tool/bioconductor:{name}:{items['Version']}/lib"
    return(items)


def import_data():
    # 1. connect to DB/ get output file
    STORAGE_MODE = os.getenv('STORAGE_MODE', 'db')
    ALAMBIQUE = os.getenv('ALAMBIQUE', 'alambique')
    print('hello, this is the bioconductor importer')

    if STORAGE_MODE =='db':
        alambique = FAIRsoft.utils.connect_collection(ALAMBIQUE)
    else:
        OUTPUT_PATH = os.getenv('OUTPUT_PATH', './')
        OUTPUT_BIOCONDUCTOR = os.getenv('OUTPUT_BIOCONDUCTOR', 'bioconductor.json')
        output_file = OUTPUT_PATH + '/' + ALAMBIQUE + '/' + OUTPUT_BIOCONDUCTOR
        print(output_file)

    
    # 2. getting arguments
    driver = webdriver.Chrome(ChromeDriverManager().install())
    arguments_parser = program_arguments_parser()
    arguments = get_program_arguments(arguments_parser)
    
    # 3. Fetch packages
    if arguments.opeb == True:
        urls_file = arguments.urls_file_path
        urls = parseInput(urls_file)
    else:
        urls = fetch_all_packages()

    log = {'names':[],
                'n_ok':0,
                'errors': []}
    if urls:
        n = 0
        print("Requesting packages URLs...")
        for url in urls:
            print("Package %d of %d"%(n, len(urls)), end='\r')
            bsO = getHTML(url, verb=False)
            n+=1
            if bsO != None:
                print('Processing BeautifulSoup Objects')
                inst_dict = retrieve_metadata(bsO, url, driver)
                print('Saving data') 

                if STORAGE_MODE=='db':
                    log = FAIRsoft.utils.push_entry(inst_dict, alambique, log)
                else:
                    print(output_file)
                    log = FAIRsoft.utils.save_entry(inst_dict, output_file, log)

    else:
        print('No URLS found')
        


if __name__ == '__main__':
    import_data()