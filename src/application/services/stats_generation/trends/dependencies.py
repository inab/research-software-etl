from datetime import datetime
from typing import List, Dict, Any
from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


'''
USAGE:
# tools = (entry['data'] for entry in collection.find({...}))
dependencies(tools, collection_name)
'''


def count_dependencies(tools: List[Dict[str, Any]]):
    """
    Computes dependencies statistics from software entries and prepares data for storage/plotting.
    """
    dependencies_stats = {}

    for entry in tools:
        entry = entry.get('data', {})
        dependencies = entry.get('dependencies', [])
        for dependency in dependencies:
            if dependency not in dependencies_stats:
                dependencies_stats[dependency] = 0
            dependencies_stats[dependency] += 1

    
    return dependencies_stats 


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




