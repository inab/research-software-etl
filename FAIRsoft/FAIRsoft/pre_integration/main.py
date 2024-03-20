'''
This script contains the transformations that are applied to the tools collection before the integration step.
'''

from pymongo.collection import Collection
import re
import os
from typing import Optional

from FAIRsoft.utils import connect_collection
from FAIRsoft.pre_integration.EDAM_forFE import EDAMDict

'''
Database connection
'''
def connect_pretools():
    mongoPretools = os.getenv('PRETOOLS', default='pretools')

    pretools = connect_collection(collection=mongoPretools)
       
    return(pretools)


'''
DONE
NORMALIZATION OF INPUT AND OUTPUT FIELDS. 
Actions needed for free-text formats are:
    1. Normalize case/equivalencies: currently the same formats are written in different cases.
    2. Mapping of free text to EDAM terms if the match between the free text and the EDAM term is perfect.
        - If match is not perfect, the format is discarded.
Actions needed for all formats are:
    3. Format normalization: Input and output currently follow two different formats.
        [
            {   "vocabulary": "EDAM",
                "term": "Sequence format",
                "uri": "http://edamontology.org/format_1929",
                datatype: {
                    "vocabulary": "EDAM",
                    "term": "Sequence",
                    "uri": "http://edamontology.org/data_0006"
                }
            },
            ...
        ]
'''

equivalencies = [
        ["textual format", "TXT", "txt", "textual", "plain text format (unformatted)"],
        ["FASTA-like","fasta-like", "fasta-like format (text)"],
        ["TSV","Tabular", "tabular", "tabular format", "tabular format (text)", "tab"],
        ["FASTQ-sanger", "fastqsanger"],
        ["YAML", 'yml', 'yaml'],
    ]

def mapEDAMDict(term: str):
    '''
    term: free text string

    Maps a free text string to an EDAM term if the match is perfect.
    '''
    for key,value in EDAMDict.items():
        if term.lower().lstrip() == value.lower():
            return(key, value, 'EDAM')

    return('', term, '')

def normalize_formats(tool:dict, field: str):
    '''
    field is either 'input' or 'output'
    '''
    if tool.get(field):
        items  = tool[field]
        new_items = []
        for item in items:
            # Free-text formats
            if 'format' in item:
                # 1. Normalize case/equivalencies 
                format = item['format']['term']
                for group in equivalencies:
                    if item['format']['term'].lower().lstrip() in group:
                        format = group[0]
                        break
                    else:
                        format = item['format']['term'].lstrip()

                # 2. Map to edam terms
                uri, term, vocabulary = mapEDAMDict(format)

                # ! Only keep formats with perfect matches
                if not vocabulary:
                    continue

                # 3. Format normalization:
                new_format = {
                    'vocabulary': vocabulary,
                    'term': term,
                    'uri': uri,
                    'datatype': {} # We cannot know the datatype from the free text
                }

                new_items.append(new_format)
            
            # EDAM formats
            else:
                # Format normalization:
                if 'datatype' in item:
                    datatype = {
                        'vocabulary': 'EDAM',
                        'term': EDAMDict[item['datatype']],
                        'uri': item['datatype']
                    }
                else:
                    datatype = {}

                for format in item['formats']:
                    new_format = {
                        'vocabulary': 'EDAM',
                        'term': EDAMDict[format],
                        'uri': format,
                        'datatype': datatype
                    }

                    new_items.append(new_format)

        tool[field] = new_items

        print(tool)
        
    return tool

'''
REFORMATING OF TOPICS AND OPERATIONS
Example of processed field:
    [
        {
            "vocabulary": "EDAM",
            "term": "Topic",
            "uri": "http://edamontology.org/topic_0003"
        },
        ...
    ]
'''

def reformat_single_topic_operation(metadata: dict, field: str, new_field: str):
    '''
    This function is used to reformat the topics and operations fields. 
    It adds the term to the topics and operations fields.
    - metadata is the tool to be processed
    - field is the field to be processed (edam_topics or edam_operations)
    - new_field is the new field to be created (topics or operations)
    '''
    items = metadata[field]
    new_items = []
    # look up for each item in the list the corresponding label
    for item in items:
        term = EDAMDict.get(item)
        if item:
            item = {
                'vocabulary': 'EDAM',
                'term': term,
                'uri': item
            }
            new_items.append(item)
    
    metadata[new_field] = new_items
    return metadata


'''
DONE
 CLEAN AND NORMALIZE LICENSES
'''

def remove_file_LICENSE(license):
    ''' remove the file LICENSE from the license name '''
    # remove +, LICENSE and file LICENSE
    license = license.replace('+', '')
    license = license.replace('LICENSE', '')
    license = license.replace('file', '')
    license = license.replace('File', '')
    license = license.replace('FILE', '')

    license = license.strip()

    return license


def prepareLicense(tool:dict):
    '''
    This function is used to clean and normalize the licenses field.
    {
        "name": "name1",
        "url": "url1"
    }
    '''
    new_licenses = []
    for license in tool['license']:
        new_lic = remove_file_LICENSE(license)
        if new_lic:
            new_license = {
                'name': new_lic,
            }
            new_licenses.append(new_license)
    
    tool['license'] = new_licenses
    return tool

'''
DONE
 MAPPING LICENSES
'''

def connect_license_collection():
    '''
    connect to the licenses collection in remote database and return the collection object
    '''
    mongoLicenses = os.getenv('LICENSES_COLLECTION', default='licensesMapping')
    licensesCollection = connect_collection(collection=mongoLicenses)

    return(licensesCollection)


def map_license(q: str, collection: Collection) -> Optional[dict]:
        '''
        This function finds the license passed as a string in the licenses collection
        The license can be found by licenseId, synonyms or name
        The license cannot be a deprecated license
        - q: license to be found
        - collection: collection object
        '''
        license = collection.find_one({ "$or": [ 
                                            { "licenseId": q }, 
                                            { "synonyms": q }, 
                                            {"name": q} 
                                            ],
                                        "isDeprecatedLicenseId": False}, {"_id": 0, "reference": 1, "licenseId":1 } )
        if license:
            return license
        else:
            return None
    

def map_build(license: str, collection: Collection) -> dict:
        '''
        This function builds the license object to be added to the tool metadata
        - license: license to be mapped
        - collection: collection object
        '''
        new_license = map_license(license, collection)
        if new_license:
            new_license = {
                'name': new_license['licenseId'],
                'url': new_license['reference']
            }
        else:
            new_license = {
                'name': license,
                'url': ''
            }
        return new_license


def prepLicense(tool:dict, collection: Collection) -> dict:
    '''
    This function is used to clean and normalize the licenses field.
    {
        "name": "name1",
        "url": "url1"
    }
    '''
    new_licenses = []
    seen_licenses = []
    for license in tool['license']:
        if license['name']:
            license = license['name'] 
            if type(license)==dict:
                license = license['name']
            
            license = license.rstrip('.')
            license = license.strip()

            if "|" in license:
                # these are various licenses
                licenses = license.split("|")
                for lic in licenses:
                    new_license = map_build(lic, collection)
                    if new_license['name'] not in seen_licenses:
                        seen_licenses.append(new_license['name'])
                        new_licenses.append(new_license)
                    else:
                        continue
            
            else:
                new_license = map_build(license, collection)
                if new_license['name'] not in seen_licenses:
                    seen_licenses.append(new_license['name'])
                    new_licenses.append(new_license)
                else:
                    continue

    tool['license'] = new_licenses
    return tool


def map_licenses():
    '''
    This function is used to map the licenses of the tools in pretools to spdx licenses
    '''
    collection = connect_license_collection()    
    for tool in pretools.find({}):
        tool = prepLicense(tool, collection)
        updateResult(tool)


'''
Prepare Description
DONE
'''
def prepareDescription(tool:dict) -> dict:

    if tool.get('description'):

        if type(tool['description']) == str:
            tool['description'] = [tool['description']]
            # TODO: throw warning here, there is an error upstream in the pipeline
    
        description = set(tool['description'])
        tool['description'] = list(description)
        # return longest description
        new_descriptions = set()
        for desc in tool['description']:
            desc=desc.capitalize()
            if desc[-1] != '.':
                desc += '.'
            new_descriptions.add(desc)
    
        # as a list for backwards compatibility
        tool['description'] = list(new_descriptions)
    
    return tool


'''
Prepare Documentation
DONE
'''

def match_url(string : str) -> bool:
        # either http or https
        pattern = re.compile(r'https?://\S+')
        if pattern.match(string):
            return True
        else:
            return False
        
def clean_documentation(documentation: list) -> list:
        '''
        Removes the documentation items that are not urls
        '''
        new_documentation = []
        for item in documentation:
            new_item = []
            if type(item[1])==str:
                if match_url(item[1]):
                    if item[0] == 'documentation':
                        new_item.append('general')
                    else:
                        new_item.append(item[0].strip())
                    new_item.append(item[1].strip())
                    new_documentation.append(new_item)

        return new_documentation

def prepareDocumentation(metadata:dict) -> dict:
    '''
    Prepares the documentation field of a tool to be displayed in the UI
    Example of processed field:
    [
        {
            "type": "documentation",
            "url": "https://bio.tools/api/tool/blast2go/docs/1.0.0"
        },
        ...
    ]
    
    '''
    items = clean_documentation(metadata['documentation'])
    new_items = []
    # look up for each item in the list the corresponding label
    for item in items:
        item = {
            'type': item[0],
            'url': item[1]
        }
        new_items.append(item)
    
    metadata['documentation'] = new_items
    
    return(metadata)


'''
Prepare Authors
'''

def clean_brakets(string):
    '''
    Remove anything between {}, [], or <>, or after {, [, <
    '''
    def clena_after_braket(string):
        '''
        Remove anything between {}, [], or <>
        '''
        pattern = re.compile(r'\{.*|\[.*|\(.*|\<.*')
        return re.sub(pattern, '', string)

    def clean_between_brakets(string):
        '''
        Remove anything between {, [, <
        '''
        pattern = re.compile(r'\{.*?\}|\[.*?\]|\(.*?\)|\<.*?\>')
        return re.sub(pattern, '', string)

    def clean_before_braket(string):
        '''
        Remove anything before }, ], or >
        '''
        pattern = re.compile(r'.*?\}.*?|.*?\].*?|.*?\>.*?')
        return re.sub(pattern, '', string)


    string = clean_between_brakets(string)
    string = clena_after_braket(string)
    string = clean_before_braket(string)

    return string

def clean_doctor(string):
    '''
    remove title at the begining of the string
    '''
    pattern = re.compile(r'^Dr\.|Dr |Dr\. |Dr')
    return re.sub(pattern, '', string)

def keep_after_code(string):
    '''
    Remove anything before code and others
    '''
    if 'initial R code' in string:
        return ''
    if 'contact form' in string:
        return ''
    else:
        pattern = re.compile(r'.*?code')
        string = re.sub(pattern, '', string)
        pattern = re.compile(r'.*?Code')
        string = re.sub(pattern, '', string)
        pattern = re.compile(r'.*?from')
        string = re.sub(pattern, '', string)
        return re.sub(pattern, '', string)

def clean_first_end_parenthesis(string):
    if string[0] == '(' and string[-1] == ')':
        string = string[1:]
        string = string[:-1]

    return string

def clean_spaces(string):
    '''
    Clean spaces around the string
    '''
    return string.strip()

def classify_person_organization(string):
    '''
    tokenize the string
    if any of the words in the string is in the list of keywords
    then it is an institution
    otherwise it is a person
    '''
    inst_keywords = [
        'university',
        'université',
        'universidad',
        'universidade',
        'università',
        'universität',
        'institut',
        'institute',
        'college',
        'school',
        'department',
        'laboratory',
        'laboratoire',
        'lab',
        'center',
        'centre',
        'research',
        'researcher',
        'researchers',
        'group',
        'support',
        'foundation',
        'company',
        'corporation',
        'team',
        'helpdesk',
        'service',
        'platform',
        'program',
        'programme',
        'community',
        'elixir'
    ]
    words = string.split()
    for word in words:
        if word.lower() in inst_keywords:
            return 'organization'
    return 'person'

def clean_long(string):
    if len(string.split()) >= 5:
        return ''
    else:
        return string


def build_organization(string):
    return {
        'type': 'organization',
        'name': string,
        'email': '',
        'maintainer': False
        }

def build_person(string):
    '''
    Extract first and last name from a string
    '''
    if string:
        return {
            'type': 'person' ,
            'name': string, 
            'email': '',
            'maintainer': False
            }
    else:
        return ''


def build_authors(authors):
    '''
    Build a list of authors
    '''
    new_authors = []
    seen_authors = set()
    for author in authors:
        name = clean_first_end_parenthesis(author)
        name = clean_brakets(name)
        name = clean_doctor(name)
        name = keep_after_code(name)
        name = clean_spaces(name)
        if name in seen_authors:
            continue
        else:
            seen_authors.add(name)
            classification = classify_person_organization(name)
            if classification == 'person':
                if name:
                    name = clean_long(name)
                    person = build_person(name)
                    new_authors.append(person)

            else:
                organization = build_organization(name)
                new_authors.append(organization)

    return new_authors

def prepareAuthors(tool):
    '''
    {
        "name": "name1",
        "email": "email1",
        "type": "person/organization",
        "maintainer": "true/false"
    }
    '''
    authors = build_authors(tool['authors'])    
    tool['authors'] = authors

    return tool
    

'''
Prepare Source Code
DONE
'''
def prepareSrc(tool):
    #print(tool['src'])
    links=set(tool['src'])
    tool['src'] = list(links)
    return tool



'''
Prepare Operating System
DONE
'''
def prepareOS(tool):
    new_os = []
    for os in tool['os']:
        if os == 'Mac':
            new_os.append('macOS')
        else:
            new_os.append(os)
    
    tool['os'] = new_os
    return tool


'''
Create Web Page
DONE
'''
def getWebPage(metadata):
    '''
    Returns the webpage of a tool
    '''
    webpages= set()
    new_links= set()
    for link in metadata['links']:
        x = re.search("^(.*)(\.)(rar|bz2|tar|gz|zip|bz|json|txt|js|py|md)$", link)
        if x:
            new_links.add(link)
        else:
            webpages.add(link)
    
    metadata['webpage'] = list(webpages)
    metadata['links'] = list(new_links)

    return metadata


def updateResult(tool:dict):
    try:
        updateResult = pretools.update_many({'@id':tool['@id']}, { '$set': tool }, upsert=True)
    except Exception as e:
        print(e)
    return


if __name__ == "__main__":
    #pass
    pretools = connect_pretools()

    # This functions should be applied to all tools pushed to pretools
    # 1. Check types

    # 2. Clean, normalize, etc data.
    
    '''
    for tool in pretools.find({}):

        tool = prepareLicense(tool)
        
        tool = reformat_single_topic_operation(tool, 'edam_topics', 'topics')
        tool = reformat_single_topic_operation(tool, 'edam_operations', 'operations')

        tool = normalize_formats(tool, 'input')
        tool = normalize_formats(tool, 'output')

        tool = prepareDescription(tool)
        tool = prepareDocumentation(tool)
        tool = prepareAuthors(tool)
        tool = prepareSrc(tool)
        tool = prepareOS(tool)

        tool = getWebPage(tool)

        updateResult(tool)

    #map_licenses()
    '''
