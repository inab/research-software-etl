from datetime import datetime
from typing import List, Dict, Any
from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


'''
USAGE: 
cursor = db.collection.find({})
tools = (entry['data'] for entry in cursor)
features_overview(tools, collection="my_stats")
'''

def features_overview(tools: List[Dict[str, Any]], collection: str):
    """
    Calculate percentage presence of standard metadata features across tools.
    """

    features_names = [
        'name', 'description', 'version', 'type', 'publication', 'download', 'webpage',
        'source_code', 'operating_system', 'input', 'output', 'dependencies', "test",
        'documentation', 'license', 'authors', 'repository', 'topics'
    ]

    feat_labels = {
        'name': 'Name',
        'description': 'Description',
        'version': 'Version',
        'type': 'Type',
        'publication': 'Publication',
        'download': 'Download',
        'webpage': 'Webpage',
        'source_code': 'Source code',
        'operating_system': 'Operating system',
        'input': 'Input format',
        'output': 'Output format',
        'dependencies': 'Dependencies',
        'test': 'Testing',
        'documentation': 'Documentation',
        'license': 'License',
        'authors': 'Authors',
        'repository': 'Repository',
        'topics': 'Topics'
    }

    def is_meaningful(value: Any) -> bool:
        if value in [None, '', 'None', 'unknown', False]:
            return False
        if value == True:
            return True
        if isinstance(value, list):
            return any(is_meaningful(v) for v in value)
        return True

    def update_dict(tool: Dict[str, Any], count_dict: Dict[str, int], feature: str) -> None:
        if feature in tool and is_meaningful(tool[feature]):
            count_dict[feature] += 1

    count_features = {feat: 0 for feat in features_names}
    total_tools = len(tools)

    for tool in tools:
        tool_data = tool.get('data', {})
        for feat in features_names:
            update_dict(tool_data, count_features, feat)

    # Convert to percentage
    features_percent = {
        feat_labels[feat]: round((count / total_tools), 1) if total_tools > 0 else 0.0
        for feat, count in count_features.items()
    }

    result = {
        'variable': 'features',
        'version': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'data': features_percent,
        'collection': collection
    }

    mongo_adapter.insert_one("computationsDev", result)