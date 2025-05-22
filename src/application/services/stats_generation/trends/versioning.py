from datetime import datetime
from typing import List, Dict, Any
from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter

'''
USAGE:
# tools = (entry['data'] for entry in collection.find({...}))
semantic_versioning(tools, collection_name)
'''


def semantic_versioning(tools: List[Dict[str, Any]], collection: str):
    """
    Computes versioning statistics from software entries and prepares data for storage/plotting.
    """

    versioning_summary = {
        'Semantic Versioning (X.Y.Z)': 0,
        'Other': 0,
        'None': 0
    }

    other_versions = []

    for entry in tools:
        entry = entry.get('data', {})
        versions = entry.get('version', [])
        version_counts = {
            'Semantic Versioning (X.Y.Z)': 0,
            'Other': 0,
            'None': 0
        }

        if not versions:
            versioning_summary['None'] += 1
            continue

        for v in versions:
            if v is None or v.strip() == '' or v.lower() == 'unknown':
                version_counts['None'] += 1
            elif v.lower() == 'v1' or len(v.split('.')) >= 2:
                version_counts['Semantic Versioning (X.Y.Z)'] += 1
            else:
                version_counts['Other'] += 1
                other_versions.append(v)

        dominant_type = max(version_counts, key=version_counts.get)
        versioning_summary[dominant_type] += 1

    # Prepare data for plot
    data = {
        'labels': ['Semantic Versioning', 'Other', 'None'],
        'values': [
            versioning_summary['Semantic Versioning (X.Y.Z)'],
            versioning_summary['Other'],
            versioning_summary['None']
        ]
    }

    data_versioning = {
        'variable': 'semantic_versioning',
        'version': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'data': data,
        'collection': collection
    }

    # Save or return this object for further processing
    mongo_adapter.insert_one("computationsDev", data_versioning)