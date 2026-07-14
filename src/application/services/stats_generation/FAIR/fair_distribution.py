from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict

    


def compute_fair_score_frequencies(results: List[Dict[str, Any]]) -> Dict[str, Dict[Any, int]]:
    """
    Compute frequency counts for FAIR indicators and subindicators across multiple tools.

    Args:
        results (List[Dict]): A list of dictionaries, each representing the FAIR evaluation result of one tool.

    Returns:
        Dict[str, Dict[Any, int]]: A dictionary where each FAIR (sub)indicator maps to a frequency count of scores.
                                   Example: {'F1': {1: 23, 0.5: 17, 0: 10}, 'F1_1': {1: 30, 0: 20}, ...}
    """
    fair_frequencies = defaultdict(lambda: defaultdict(int))

    for result in results:
        result = result['data']
        
        for key, value in result.items():
            # Skip non-FAIR keys
            if key in {"name", "type", "version"}:
                continue
            # Count only meaningful numerical scores
            if value is not None:
                fair_frequencies[key][value] += 1

    # Convert nested defaultdicts to regular dicts for output
    return {indicator: dict(score_counts) for indicator, score_counts in fair_frequencies.items()}


def build_summary_scores(distribution):
    '''
    given a dictionary of frequencies of scores for all indicators, 
    builds a summary dictionary suitable to build plots 
    {
        F: [
            {
                indicator: F1,
                scores: [0.8, 1.0],
                count:  [25397, 18590],
                percent: [0.58, 0.42]
            },
            ...    
        ],
        ...
    }
    '''
    indicators = {
        'F': ['F1', 'F2', 'F3'],
        'A': ['A1', 'A3'],
        'I': ['I1', 'I2', 'I3'],
        'R': ['R1', 'R2', 'R3', 'R4']
    }
    summary = {
        'F':[],
        'A':[],
        'I':[],
        'R':[]
    }
    for principle in indicators.keys():
        for indicator in indicators[principle]:
            indicator_scores = distribution[principle][indicator]
            total = sum([indicator_scores[s] for s in indicator_scores.keys()])
            indicator_summary  = {
                'indicator': indicator,
                'scores': [s for s in indicator_scores.keys()],
                'count' : [indicator_scores[s] for s in indicator_scores.keys()],
                'percent' : [indicator_scores[s]/total for s in indicator_scores.keys()] 
            }
            summary[principle].append(indicator_summary)
    
    return(summary)

def compute_fair_score_means(results: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Compute mean scores for all FAIR indicators and subindicators.

    Args:
        results (List[Dict]): A list of result dicts containing FAIR scores for one tool each.

    Returns:
        Dict[str, float]: A dictionary where keys are indicators (e.g., 'F1', 'F1_1', etc.)
                          and values are the mean score across tools (ignoring None).
    """
    score_sums = defaultdict(float)
    score_counts = defaultdict(int)

    indicators = ['F','F1', 'F2', 'F3', 'A', 'A1', 'A3', 'I', 'I1', 'I2', 'I3','R', 'R1', 'R2', 'R3', 'R4']
    for result in results:
        result = result['data']
        for key, value in result.items():
            if key not in indicators:
                continue
            if value is not None:
                score_sums[key] += value
                score_counts[key] += 1

    # Compute means
    means = {
        key: round(score_sums[key] / score_counts[key], 4)
        for key in score_sums
        if score_counts[key] > 0
    }

    return means


def _tool_key(created_from):
    """
    The tool a FAIR-score document was computed from.

    `createdFrom` is a one-element *list* of the tool id -- it was migrated from a
    bare string by scripts/utils/db_createdFrom_to_list.py. Using the list itself
    as a dict key raised `TypeError: unhashable type: 'list'`, which is to say this
    dedup never ran after that migration.
    """
    if isinstance(created_from, list):
        return created_from[0] if created_from else None
    return created_from


def get_fair_scores(collection, computations):
    """The most recent FAIR score per tool."""
    tag = None if collection == 'tools' else collection
    entries = computations.find_by_variable("FAIR_scores", tag=tag)

    latest_by_tool = {}

    for entry in entries:
        tool_id = _tool_key(entry.get("createdFrom"))
        version = entry.get("version")

        if not tool_id or not version:
            continue

        version_dt = datetime.fromisoformat(version)
        current = latest_by_tool.get(tool_id)

        if current is None or version_dt > datetime.fromisoformat(current["version"]):
            latest_by_tool[tool_id] = entry

    return list(latest_by_tool.values())


def do_sanity_check(collection, repos):

    # tools
    if collection == 'tools':
        tools_entries = repos.tools.get_all()
    else:
        # Tags live under `data` on a tool; the top-level `tags` this used to query
        # does not exist there, so it always found nothing.
        tools_entries = repos.tools.find({'data.tags': collection})

    tag = None if collection == 'tools' else collection
    fair_entries = repos.computations.find_by_variable("FAIR_scores", tag=tag)

    if len(tools_entries) != len(fair_entries):
        print("WARNING: different number of tools and FAIR scores records")
        print(f"{len(tools_entries)} tools vs {len(fair_entries)} score records")
    else:
        print("Same number of tools and FAIR score records")

    return


def compute_fair_distributions(collection, repos):

    do_sanity_check(collection, repos)

    results = get_fair_scores(collection, repos.computations)
    print(f"Results for {collection}: {len(results)} documents")


    frequencies = compute_fair_score_frequencies(results)

    new_freqs = {
        'F': {},
        'A': {},
        'I': {},
        'R': {}
    }

    for key in frequencies.keys():
        if key.startswith('F'):
            new_freqs['F'][key] = frequencies[key]
        elif key.startswith('A'):
            new_freqs['A'][key] = frequencies[key]
        elif key.startswith('I'):
            new_freqs['I'][key] = frequencies[key]
        elif key.startswith('R'):
            new_freqs['R'][key] = frequencies[key]
    

    summary =  build_summary_scores(new_freqs)
    means = compute_fair_score_means(results)

    data = {
        'variable': 'FAIR_scores_summary',
        'version': datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'data': summary,
        'collection': collection
    }

    repos.computations.save(data)

    data_2 = {
        'variable': 'FAIR_scores_means',
        'version': datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'data': means,
        'collection': collection
    }

    repos.computations.save(data_2)

