from datetime import datetime
from typing import List, Dict, Any


'''
USAGE
cursor = db.mycollection.find({})
count_tools(cursor, "my_collection")  # safe with cursors
count_tools_per_source(cursor, "my_collection")
'''

def count_tools_per_source(tools: List[Dict[str, Any]], collection: str, computations):
    """
    Count number of tools per curated source label.
    """

    # Canonical source mapping
    source_match = {
        'bioconda': 'bioconda',
        'bioconda_recipes': 'bioconda',
        'bioconda_conda': 'bioconda',
        'galaxy_metadata': 'toolshed',
        'toolshed': 'toolshed',
        'github': 'github',
        'biotools': 'biotools',
        'bioconductor': 'bioconductor',
        'sourceforge': 'sourceforge',
        'bitbucket': 'bitbucket',
        'opeb_metrics': 'opeb_metrics',
        'galaxy': 'galaxy'
    }

    # Initialize counts for known labels
    source_labels = set(source_match.values())
    counts = {label: 0 for label in source_labels}

    for entry in tools:
        entry = entry.get('data', {})
        raw_sources = entry.get('source', [])
        # Map and deduplicate sources
        mapped_sources = {source_match[s] for s in raw_sources if s in source_match}
        for src in mapped_sources:
            counts[src] += 1

    data = [{"source": src, "count": counts[src]} for src in counts]

    count_source = {
        'variable': 'tools_counts_per_source',
        'version': datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'data': data,
        'collection': collection,
        'createdFrom': [tool['_id'] for tool in tools],
        'createdAt': datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    }

    computations.save(count_source)


def count_tools(tools: List[Dict[str, Any]], collection: str, computations):
    """
    Count total number of tools.
    """
    count = {
        'variable': 'tools_count',
        'version': datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'data': sum(1 for _ in tools),  # handles cursor or list
        'collection': collection,
        'createdFrom': [tool['_id'] for tool in tools],
        'createdAt': datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    }

    computations.save(count)