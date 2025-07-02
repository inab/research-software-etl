from datetime import datetime
from typing import List, Dict, Any
from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from collections import Counter


'''
USAGE:
# tools = (entry['data'] for entry in collection.find({...}))
dependencies(tools, collection_name)
'''


def count_dependencies(tools: List[Dict[str, Any]]):
    """
    Computes dependencies statistics from software entries and prepares data for storage/plotting.
    Returns only the top 10 most common dependencies.
    """
    dependencies_counter = Counter()

    for entry in tools:
        entry = entry.get('data', {})
        dependencies = entry.get('dependencies', [])
        dependencies_counter.update(dependencies)

    # Get the 10 most common dependencies
    top_20 = dict(dependencies_counter.most_common(20))
    return top_20


def dependencies_count(dependencies_stats: Dict[str, int], collection: str):
    """
    Prepares data for storage/plotting.
    """
    dependencies_summary = {
        'variable': 'dependencies_count',
        'version': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'data': dependencies_stats,
        'collection': collection
    }

    return dependencies_summary



def dependencies(tools: List[Dict[str, Any]], collection: str):
    dependencies_stats = count_dependencies(tools)
    dependencies_summary = dependencies_count(dependencies_stats, collection)

    # Save or return this object for further processing
    mongo_adapter.insert_one("computationsDev", dependencies_summary)




