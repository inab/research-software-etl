from datetime import datetime
from typing import List, Dict, Any
from collections import Counter
import re

'''
USAGE:
# tools = (entry['data'] for entry in collection.find({...}))
dependencies(tools, collection_name)
'''

def clean_dependency(dep: str) -> str:
    # Remove version specifiers like '>= 1.2', '<= 2.0', '==1.0', etc.
    dep = re.split(r'\s*[<>=!~]+\s*', dep)[0]
    # Remove anything like '(' or trailing spaces
    return re.sub(r'\s*\(.*$', '', dep).strip()

def count_dependencies(tools: List[Dict[str, Any]]):
    """
    Computes cleaned dependency statistics from software entries and prepares data for storage/plotting.
    Returns only the top 20 most common dependencies.
    """
    dependencies_counter = Counter()
    tools_w_deps = 0
    for entry in tools:
        entry = entry.get('data', {})
        dependencies = entry.get('dependencies', [])

        if len(dependencies) > 0:
            tools_w_deps += 1

        cleaned_deps = [clean_dependency(dep) for dep in dependencies]
        dependencies_counter.update(cleaned_deps)

    # Get the 20 most common cleaned dependencies
    top_20 = dict(dependencies_counter.most_common(20))

    return top_20, tools_w_deps


def dependencies_count(dependencies_stats: Dict[str, int], collection: str, computations):
    """
    Prepares data for storage/plotting.
    """
    dependencies_summary = {
        'variable': 'dependencies_count',
        'version': datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'data': dependencies_stats,
        'collection': collection
    }

    return dependencies_summary


def dependencies_coverage(tools, tools_w_deps, collection, computations):

    data = {
        'count': tools_w_deps,
        'percentage': tools_w_deps/len(list(tools))
    }

    doc = {
        'variable':'dependencies_coverage',
        'createdAt': datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'version': datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'data': data,
        'collection': collection
    }

    return doc


def dependencies(tools: List[Dict[str, Any]], collection: str, computations):
    dependencies_stats, tools_w_deps = count_dependencies(tools)
    created_from = [tool['_id'] for tool in tools]

    dependencies_summary = dependencies_count(dependencies_stats, collection, computations)
    dependencies_summary['createdAt'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    dependencies_summary['createdFrom'] = created_from
    computations.save(dependencies_summary)

    dependencies_coverage_doc = dependencies_coverage(tools, tools_w_deps, collection, computations)
    dependencies_coverage_doc['createdAt'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    dependencies_coverage_doc['createdFrom'] = created_from
    computations.save(dependencies_coverage_doc)




