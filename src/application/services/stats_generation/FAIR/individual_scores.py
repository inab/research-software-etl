from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from bson import ObjectId
from pprint import pprint
import requests 


def get_pub(object_id):
    from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter

    publication = mongo_adapter.fetch_entry( "publicationsMetadataDev", object_id)    
    if publication:
        return publication.get('data')
    else:
        return None


def request_fair_calculation(entry) -> None:
    
    URL ="https://observatory.openebench.bsc.es/api/fair/evaluate"
    #URL ="http://127.0.0.1:8000/fair/evaluate"
    body = {
        'tool_metadata': entry,
        "prepare": False
    }
    request = requests.post(URL, json=body)
    # request fair calculation
    if request.status_code == 200:
        result = request.json()
    else:
        print(f"Error: {request.status_code}")
        print(f"Error: {request.text}")
        return None

    return result['result']

def prep_entry_for_evaluation(entry):

    publications_records = set()

    id = str(entry.get('_id'))
    entry = entry.get('data', {})
    publications_new = []
    if entry.get('publication'):
        for pub in entry['publication']:
            publication = get_pub(ObjectId(pub))
            if publication:
                publications_records.add(id)
                if 'citations' in publication:
                    del publication['citations']
                if 'abstract' in publication:
                    del publication['abstract']
            
                publications_new.append(publication)
        
    entry['publication'] = publications_new

    if entry.get('type'):
        if len(entry.get('type', []))>1:
            entry['other_types'] = entry.get('type', [])[1:]
            entry['type'] = entry.get('type', [])[0]
        else:
            entry['other_types'] = []
            entry['type'] = entry.get('type', [])[0]
    else:
        entry['type'] = None
        entry['other_types'] = []

    if entry.get('version'):
        if len(entry.get('version', []))>1:
            entry['other_versions'] = entry.get('version', [])[1:]
            entry['version'] = entry.get('version', [])[0]
        else:
            entry['other_versions'] = []
            entry['version'] = entry.get('version', [])[0]
    else:
        entry['version'] = None
        entry['other_versions'] = []


    if entry['authors'] is None:
        entry['authors'] = []
    else:
        for author in entry['authors']:
            if author['type'] == None:
                author['type'] = 'unknown'
            if author['name'] == None:
                author['name'] = 'unknown'
            if author['email'] == None:
                author['email'] = ''


    repos = []
    if entry['repository']:
        for repo in entry['repository']:
            if repo.get('url'):
                repos.append(repo['url'])
    entry['repository'] = repos

    if entry['test'] is True:
        entry['test'] = ['https://openebech.bsc.es']
    else:
        entry['test'] = []

    if entry['source_code']:
        entry['src'] = entry['source_code']
    else:
        entry['src'] = []

    if entry['operating_system']:
        entry['os'] = entry['operating_system']
    else:
        entry['os'] = []

    return entry



def evaluate_tool(entry):
    
    entry = prep_entry_for_evaluation(entry)

    #result = { id: request_fair_calculation(entry)}

    result = request_fair_calculation(entry)

    return result

