from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from collections import Counter
from pprint import pprint
from bson import ObjectId


def calculate_R4(collection):

    if collection == 'tools':
        tools = mongo_adapter.fetch_entries("toolsDev", {})
    else:
        tools = mongo_adapter.fetch_entries("toolsDev", {'data.tags': collection})

    # calculate scores 
    R4_scores = []
    for tool in tools:
        tool_R4 = 0
        if tool['data']['repository'] and tool['data']['repository'] != 'None':
            for repo in tool['data']['repository']:
                if repo['kind'] in ['github', 'gitlab', 'bitbucket', 'bioconductor']:
                    tool_R4 = 1
                    
        R4_scores.append(tool_R4)

    print(f"Number of tools: {len(tools)}")
    print(f"Number of R4 scores: {len(R4_scores)}")

    assert len(tools) == len(R4_scores), f"Number of tools and R4 scores do not match: {len(tools)} != {len(R4_scores)}"

    # calcualte distribution
    R4_distribution = Counter(R4_scores)
    print(f"R4 distribution: {R4_distribution}")

    return R4_distribution


if __name__ == "__main__":
    collections = ['Proteomics', 'tools']

    # Run the script for each collection
    for collection in collections:
        print(f" ------ Processing collection: {collection}  ---------")
        R4_distribution = calculate_R4(collection)
        scores = []
        count = []
        for k, v in R4_distribution.items():
            scores.append(k)
            count.append(v)

        new_R4 = {
            'indicator': 'R4',
            'scores': scores,
            'count': count,
            'percent': [(c / sum(count)) for c in count]
        }

        # load other R indicators
        query = {
            'variable': 'FAIR_scores_summary',
            'collection': collection
        }

        R_scores_old = mongo_adapter.fetch_entry('computationsDev', query)

        R_indicators_old = R_scores_old['data']['R']

        for indicator in R_indicators_old:
            if indicator['indicator'] == 'R4':
                # update the R4 indicator
                indicator['scores'] = new_R4['scores']
                indicator['count'] = new_R4['count']
                indicator['percent'] = new_R4['percent']
                break

        
        id = ObjectId(R_scores_old['_id'])
        mongo_adapter.update_entry(
            'computationsDev',
            id,
            {
                'data.R': R_indicators_old
            }
        )
        

        print(f" New indicators:")
        pprint(R_indicators_old)
        

        
    
    # Run the script for a specific collection
