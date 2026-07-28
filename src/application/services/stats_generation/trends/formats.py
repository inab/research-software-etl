from datetime import datetime
from typing import List, Dict, Any




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

    total = len(list(tools))
    data = {
        'count': tools_w_format,
        # A collection with no tools has 0% coverage, not a crash.
        'percentage': (tools_w_format / total) if total else 0
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


def formats(tools: List[Dict[str, Any]], collection: str, computations):
    input_formats_counts = count_input_formats(tools)
    output_formats_counts = count_output_formats(tools)
    created_from = [tool['_id'] for tool in tools]


    input_formats_summary = formats_stats(input_formats_counts, 'input_formats', collection)
    input_formats_summary['createdAt'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    input_formats_summary['createdFrom'] = created_from
    computations.save(input_formats_summary)

    output_formats_summary = formats_stats(output_formats_counts, 'output_formats', collection)
    output_formats_summary['createdAt'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    output_formats_summary['createdFrom'] = created_from
    computations.save(output_formats_summary)

    tools_w_formats = formats_coverage(tools)
    formats_coverage_doc = coverage_doc(tools, tools_w_formats, collection)
    formats_coverage_doc['createdAt'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    formats_coverage_doc['createdFrom'] = created_from
    computations.save(formats_coverage_doc)


