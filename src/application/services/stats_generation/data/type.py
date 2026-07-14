from datetime import datetime
from typing import List, Dict, Any
from collections import Counter

'''
USAGE
tools = (entry['data'] for entry in db.mytools.find({}))
count_types_tools(tools, "my_stats")
'''

def count_types_tools(tools: List[Dict[str, Any]], collection: str, computations):
    """
    Calculates the percentage of each tool type across the dataset.
    """

    type_counter = Counter()
    total_type_occurrences = 0

    for tool in tools:
        tool = tool.get('data', {})
        types = tool.get('type', [])
        if not isinstance(types, list):
            types = [types] if types else []
        filtered_types = [t for t in types if t and t != 'unknown' and t != 'None']
        type_counter.update(filtered_types)
        total_type_occurrences += len(filtered_types)

    type_percentages = {
        t: round((count / total_type_occurrences), 2)
        for t, count in type_counter.items()
    }

    types_count = {
        'variable': 'types_count',
        'version': datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'data': type_percentages,
        'collection': collection,
        'createdFrom': [tool['_id'] for tool in tools],
        'createdAt': datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    }

    computations.save(types_count)