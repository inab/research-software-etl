from datetime import datetime
from typing import List, Dict, Any
from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter

'''
tools = (entry['data'] for entry in db.collection.find({}))
coverage_sources(tools, "my_stats")
'''

def coverage_sources(tools: List[Dict[str, Any]], collection: str):
    """
    Computes how many sources contribute to each tool, and how many tools are present per source combination.
    """

    # Source normalization
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
        'galaxy': 'galaxy'
    }

    sources_lab = set(source_match.values())
    bucket_keys = [str(i) for i in range(1, 10)]

    Counts = {k: 0 for k in bucket_keys}
    Counts_cummulative = {k: 0 for k in bucket_keys}
    count_source = {label: {} for label in sources_lab}

    for tool in tools:
        tool = tool.get('data', {})
        raw_sources = tool.get('source', [])
        mapped_sources = list({source_match[s] for s in raw_sources if s in source_match})
        num_sources = len(mapped_sources)

        if 1 <= num_sources <= 9:
            bucket = str(num_sources)
            Counts[bucket] += 1

            for src in mapped_sources:
                if bucket not in count_source[src]:
                    count_source[src][bucket] = 1
                else:
                    count_source[src][bucket] += 1

    # Cumulative counts
    total = 0
    for k in bucket_keys:
        total += Counts[k]
        Counts_cummulative[k] = total

    # Prepare per-source count distribution (for bar charts)
    new_counts = {}
    for src in count_source:
        counts = [count_source[src].get(k, 0) for k in bucket_keys[:6]]  # only up to 6
        new_counts[src] = counts

    data = {
        'counts': new_counts,
        'counts_cummulative': Counts_cummulative,
    }

    result = {
        'variable': 'coverage_sources',
        'version': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'data': data,
        'collection': collection
    }

    mongo_adapter.insert_one("computationsDev", result)

