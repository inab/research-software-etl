from datetime import datetime
from typing import List, Dict, Any
from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from collections import Counter
from collections import defaultdict
from pprint import pprint

import re



def add_counts(new_items, counts_dict):
    for item in new_items:
        if item['term']:
            if item['term'] in counts_dict.keys():
                counts_dict[item['term']] += 1
            else:
                counts_dict[item['term']] = 1
    
    return counts_dict


def count_input_formats(tools: List[Dict[str, Any]]):
    formats_counts = {}
    for tool in tools:
        if tool['data']['input']:
            formats_counts = add_counts(tool['data']['input'], formats_counts)
        
    return formats_counts


def count_output_formats(tools: List[Dict[str, Any]]):
    formats_counts = {}
    for tool in tools:
        if tool['data']['output']:
            formats_counts = add_counts(tool['data']['output'], formats_counts)
    
    return formats_counts

def formats_coverage(tools):
    tools_w_formats = 0
    for tool in tools:
        if tool['data']['input']:
            tools_w_formats += 1
            continue
        if tool['data']['output']:
            tools_w_formats += 1

    return tools_w_formats

def coverage_doc(tools, tools_w_format, collection):

    data = {
        'count': tools_w_format,
        'percentage': tools_w_format/len(list(tools))
    }

    doc = {
        'variable': 'formats_coverage',
        'version': datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'data': data, 
        'collection': collection
    }

    return doc



def formats_stats(format_counts, variable_name, collection):
    summary = {
        'variable' : variable_name,
        'version' : datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'data' : format_counts,
        'collection': collection 
    }

    return summary 


def formats(tools: List[Dict[str, Any]], collection: str):
    input_formats_counts = count_input_formats(tools)
    output_formats_counts = count_output_formats(tools)

    input_formats_summary = formats_stats(input_formats_counts, 'input_formats', collection)
    mongo_adapter.insert_one('computationsDev', input_formats_summary)

    output_formats_summary = formats_stats(output_formats_counts, 'output_formats', collection)
    mongo_adapter.insert_one('computationsDev', output_formats_summary)

    tools_w_formats = formats_coverage(tools)
    formats_coverage_doc = coverage_doc(tools, tools_w_formats, collection)
    mongo_adapter.insert_one('computationsDev', formats_coverage_doc)


