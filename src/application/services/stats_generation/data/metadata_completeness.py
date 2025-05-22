from datetime import datetime
from typing import List, Dict, Any
from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter

'''
USAGE:
tools = (entry['data'] for entry in db.mytools.find({}))
features_cummulative(tools, "my_stats")
features_xy(tools, "my_stats")
'''


all_features = [
    "name",
    "type",
    "version",
    "label",
    "description",
    "source_code",
    "download",
    "license",
    "documentation",
    "operating_system",
    "repository",
    "webpage",
    "input",
    "output",
    "dependencies",
    "authors",
    "publication",
    "topics",
    "operations",
    "test"
]

def is_value_meaningful(value: Any) -> bool:
    """
    Check if a value is meaningful (not None, empty, or 'unknown').
    """
    if value in [None, '', 'None', 'unknown', False]:
        return False
    if value == True:
        return True
    if isinstance(value, list):
        return any(is_value_meaningful(v) for v in value)
    return True

def is_meaningful(key, value):
    if key in all_features:
        if value in [None, '', 'None', 'unknown']:
            return False
        if isinstance(value, list):
            return any(is_value_meaningful(v) for v in value)

        return True
    
    else: 
        return False
    


def features_cummulative(tools: List[Dict[str, Any]], collection: str):
    """
    Computes the cumulative percentage of tools with a given number of meaningful features.
    """

    def count_features(tool: Dict[str, Any]) -> int:
        return sum(1 for k,v in tool.items() if is_meaningful(k,v))

    counts = [count_features(tool['data']) for tool in tools]
    total_tools = len(tools)

    feat_num = []
    count_cumm_pct = []

    cumulative = 0
    for number in sorted(set(counts)):
        count = counts.count(number)
        cumulative += count
        feat_num.append(number)
        count_cumm_pct.append(round((cumulative / total_tools), 2))  # as percentage

    data = {
        'feat_num': feat_num,
        'count_cumm_pct': count_cumm_pct
    }

    feats_cummulative = {
        'variable': 'features_cummulative',
        'version': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'data': data,
        'collection': collection
    }

    mongo_adapter.insert_one("computationsDev", feats_cummulative)


from collections import Counter


def features_xy(tools: List[Dict[str, Any]], collection: str):
    """
    Calculates the percentage of tools that have N meaningful features.
    X: number of features, Y: percentage of tools with that number.
    """

    def count_features(tool: Dict[str, Any]) -> int:
        return sum(1 for k,v in tool.items() if is_meaningful(k,v))

    counts = [count_features(tool['data']) for tool in tools]
    counter = Counter(counts)
    total = len(tools)

    data = {
        'y': sorted(counter.keys()),
        'x': [round((counter[k] / total), 2) for k in sorted(counter.keys())]  # percentages with 2 decimals
    }

    feats_xy = {
        'variable': 'distribution_features',
        'version': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'data': data,
        'collection': collection
    }


    mongo_adapter.insert_one("computationsDev", feats_xy)