from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from collections import defaultdict
from datetime import datetime

from bson import ObjectId

def compute_journal_impact(docs, years=['2022', '2023', '2024']):
    """
    Compute total citations in selected years per journal and collect document IDs.
    
    Args:
        docs (list): List of documents from MongoDB.
        years (list): List of years to include in impact calculation. If None, use 'total'.
    
    Returns:
        dict: journal -> {'impact': int, 'ids': list of _id}
    """
    N = 0
    n_citations = 0
    n_journals = 0
    journal_impact = defaultdict(lambda: {"impact": 0, "ids": []})

    for doc in docs:
        if not doc.get("data"):
            continue
        
        N += 1
        journal = doc.get("data", {}).get("journal")
        citations = doc.get("data", {}).get("citations")
        doc_id = doc.get("_id")

        if not journal or not citations:
            continue
        
        n_journals += 1
        for c in citations:
            if c.get("source") == "Semantic Scholar":
                
                counts = c.get("count")
                if not counts:
                    continue
                
                n_citations += 1
                impact = sum(counts.get(y, 0) for y in years)
            
                journal_impact[journal]["impact"] += impact
                journal_impact[journal]["ids"].append(doc_id)

    print("----- Summary -----")
    print(f"Total publications: {N}")
    print(f"Total publications with journals: {n_journals}")
    print(f"Total publications with citations: {n_citations}")
    print(f"Total journals: {len(journal_impact)}")
    print('-----------------')
    
    return journal_impact

def get_top_journals(journal_impact, top_n=10):
    return sorted(journal_impact.items(), key=lambda x: x[1]["impact"], reverse=True)[:top_n]


def number_of_tools(publication_ids, tools):
    n = 0
    for entry in tools:
        publications = entry['data'].get("publication", [])
        for publication in publications:
            if ObjectId(publication) in publication_ids:
                n += 1

    return n
    

def publications_journals_IF(collection):

    if collection == 'tools':
        tools = mongo_adapter.fetch_entries("toolsDev", {})
    else:
        tools = mongo_adapter.fetch_entries("toolsDev", { 'data.tags': collection })

    docs = []
    if collection != 'tools':
        for tool in tools:
            if tool.get("data"):
                if tool['data'].get("publication"):
                    for publication_id in tool['data']['publication']:
                        doc = mongo_adapter.fetch_entry("publicationsMetadataDev", {"_id": ObjectId(publication_id)})
                        if doc:
                            docs.append(doc)
    else:
        docs = mongo_adapter.fetch_entries("publicationsMetadataDev", {})
        

    journal_impact = compute_journal_impact(docs)
    top_journals = get_top_journals(journal_impact)

    
    print('----------------- Top Journals -------------------')

    for journal, data in top_journals:
        print(f"Journal: {journal}, Impact: {data['impact']}, Number of publications: {len(data['ids'])}")

    print('-----------------------------------------------')

    #  generating percentage_tools
    _tools = {
        'y': [],
        'x': []
    }

    _publications = {
        'y': [],
        'x': []
    }

    citations = {
        'y': [],
        'x': []
    }


    for journal, data in top_journals:
        _publications['x'].append(journal)
        _publications['y'].append(len(data['ids']))

        _tools['x'].append(journal)
        n_tools = number_of_tools(data['ids'], tools)
        _tools['y'].append(n_tools)

        citations['x'].append(journal)
        citations['y'].append(data['impact'])

    result = {
        'variable': 'publications_journals_IF',
        'version': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'data': {
            'tools': _tools,
            'publications': _publications,
            'citations': citations
        },
        'collection': collection
    }

    mongo_adapter.insert_one("computationsDev", result)


