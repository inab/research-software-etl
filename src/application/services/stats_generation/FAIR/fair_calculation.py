from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any
from bson import ObjectId
from pprint import pprint
import requests 
import json

def get_pub(object_id):
    from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter

    publication = mongo_adapter.fetch_entry( "publicationsMetadataDev", object_id)    
    if publication:
        return publication.get('data')
    else:
        return None
    

from collections import defaultdict
from typing import List, Dict, Any

def compute_fair_score_frequencies(results: List[Dict[str, Any]]) -> Dict[str, Dict[Any, int]]:
    """
    Compute frequency counts for FAIR indicators and subindicators across multiple tools.

    Args:
        results (List[Dict]): A list of dictionaries, each representing the FAIR evaluation result of one tool.

    Returns:
        Dict[str, Dict[Any, int]]: A dictionary where each FAIR (sub)indicator maps to a frequency count of scores.
                                   Example: {'F1': {1: 23, 0.5: 17, 0: 10}, 'F1_1': {1: 30, 0: 20}, ...}
    """
    fair_frequencies = defaultdict(lambda: defaultdict(int))

    for result in results:
        for key, value in result.items():
            # Skip non-FAIR keys
            if key in {"name", "type", "version"}:
                continue
            # Count only meaningful numerical scores
            if value is not None:
                fair_frequencies[key][value] += 1

    # Convert nested defaultdicts to regular dicts for output
    return {indicator: dict(score_counts) for indicator, score_counts in fair_frequencies.items()}


def build_summary_scores(distribution):
    '''
    given a dictionary of frequencies of scores for all indicators, 
    builds a summary dictionary suitable to build plots 
    {
        F: [
            {
                indicator: F1,
                scores: [0.8, 1.0],
                count:  [25397, 18590],
                percent: [0.58, 0.42]
            },
            ...    
        ],
        ...
    }
    '''
    indicators = {
        'F': ['F1', 'F2', 'F3'],
        'A': ['A1', 'A3'],
        'I': ['I1', 'I2', 'I3'],
        'R': ['R1', 'R2', 'R3', 'R4']
    }
    summary = {
        'F':[],
        'A':[],
        'I':[],
        'R':[]
    }
    for principle in indicators.keys():
        for indicator in indicators[principle]:
            indicator_scores = distribution[principle][indicator]
            total = sum([indicator_scores[s] for s in indicator_scores.keys()])
            indicator_summary  = {
                'indicator': indicator,
                'scores': [s for s in indicator_scores.keys()],
                'count' : [indicator_scores[s] for s in indicator_scores.keys()],
                'percent' : [indicator_scores[s]/total for s in indicator_scores.keys()] 
            }
            summary[principle].append(indicator_summary)
    
    return(summary)

def compute_fair_score_means(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Compute mean scores for all FAIR indicators and subindicators.

    Args:
        results (List[Dict]): A list of result dicts containing FAIR scores for one tool each.

    Returns:
        Dict[str, float]: A dictionary where keys are indicators (e.g., 'F1', 'F1_1', etc.)
                          and values are the mean score across tools (ignoring None).
    """
    score_sums = defaultdict(float)
    score_counts = defaultdict(int)

    indicators = ['F1', 'F2', 'F3', 'A1', 'A3', 'I1', 'I2', 'I3', 'R1', 'R2', 'R3', 'R4']
    for result in results:
        for key, value in result.items():
            if key not in indicators:
                continue
            if value is not None:
                score_sums[key] += value
                score_counts[key] += 1

    # Compute means
    means = {
        key: round(score_sums[key] / score_counts[key], 4)
        for key in score_sums
        if score_counts[key] > 0
    }

    return means


def request_fair_calculation(entry) -> None:
    
    #URL ="https://observatory.openebench.bsc.es/api/fair/evaluate"
    URL ="http://127.0.0.1:8000/fair/evaluate"
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


def compute_fair_results(tools):
    results = []
    publications_records = set()
    for entry in tools:
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


        result = { id: request_fair_calculation(entry)}

        #result = request_fair_calculation(entry)

        if result is None:
            print("request response is None")
            exit(1)
        
        #results.append(result)
    
        #results.append(result)
    
        with open('scripts/data/fair_results.jsonl', 'a') as f:
            f.write(json.dumps(result) + '\n')


def compute_fair_results_collections(tools):
    results = []
    publications_records = set()
    for entry in tools:
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


        #result = { id: request_fair_calculation(entry)}

        result = request_fair_calculation(entry)

        if result is None:
            print("request response is None")
            exit(1)
        
        results.append(result)
    
        #results.append(result)
    
        #with open('scripts/data/fair_results.jsonl', 'a') as f:
        #    f.write(json.dumps(result) + '\n')

    print(f"Number of records with publications: {len(publications_records)}")
    print(f"Number of records: {len(tools)}")
    return results

def compute_fair_distributions(tools, collection):

    results = compute_fair_results_collections(tools)

    #compute_fair_results(tools)

    #results = []
    
    #with open('scripts/data/fair_results.jsonl', 'r') as f:
    #    for line in f:
    #        whole_dict = json.loads(line)
    #        for key in whole_dict.keys():
    #            results.append(whole_dict[key])
    

    # Assume `results` is a list of dicts like the one you showed
    
    frequencies = compute_fair_score_frequencies(results)

    new_freqs = {
        'F': {},
        'A': {},
        'I': {},
        'R': {}
    }

    for key in frequencies.keys():
        if key.startswith('F'):
            new_freqs['F'][key] = frequencies[key]
        elif key.startswith('A'):
            new_freqs['A'][key] = frequencies[key]
        elif key.startswith('I'):
            new_freqs['I'][key] = frequencies[key]
        elif key.startswith('R'):
            new_freqs['R'][key] = frequencies[key]
    

    summary =  build_summary_scores(new_freqs)
    means = compute_fair_score_means(results)

    data = {
        'variable': 'FAIR_scores_summary',
        'version': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'data': summary,
        'collection': collection
    }

    mongo_adapter.insert_one("computationsDev", data)

    data_2 = {
        'variable': 'FAIR_scores_means',
        'version': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'data': means,
        'collection': collection
    }

    mongo_adapter.insert_one("computationsDev", data_2)

