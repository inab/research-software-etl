from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from collections import defaultdict
from datetime import datetime

from bson import ObjectId

def compute_journal_impact(docs, years=['2022', '2023', '2024', '2025']):
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

def tools_w_publication(tools):
    n=0
    for entry in tools:
        publications = entry['data'].get("publication", [])
        if len(publications) > 0:
            n += 1

    return n



def _to_oid(x):
    """Coerce x into an ObjectId if possible, else return None."""
    if isinstance(x, ObjectId):
        return x
    if isinstance(x, str):
        try:
            return ObjectId(x)
        except Exception:
            return None
    if isinstance(x, dict):
        # Common JSON export shape: {"$oid": "..."} or {"oid": "..."}
        for k in ("$oid", "oid", "_id"):
            if k in x and isinstance(x[k], str):
                try:
                    return ObjectId(x[k])
                except Exception:
                    return None
    return None

def publications_journals_IF(collection):
    # 1) Fetch tools (materialize)
    if collection == 'tools':
        tools = list(mongo_adapter.fetch_entries("toolsDev", {}))
    else:
        tools = list(mongo_adapter.fetch_entries("toolsDev", { 'data.tags': collection }))

    # 2) Build publications doc list robustly
    if collection != 'tools':
        docs = []
        for tool in tools:
            data = tool.get("data") or {}
            pubs = data.get("publication") or []
            for p in pubs:
                oid = _to_oid(p)
                if not oid:
                    continue
                doc = mongo_adapter.fetch_entry("publicationsMetadataDev", {"_id": oid})
                if doc:
                    docs.append(doc)
    else:
        docs = list(mongo_adapter.fetch_entries("publicationsMetadataDev", {}))

    # 3) Compute & report
    journal_impact = compute_journal_impact(docs, years=['2022','2023','2024','2025'])
    top_journals = get_top_journals(journal_impact)

    print('----------------- Top Journals -------------------')
    for journal, data in top_journals:
        print(f"Journal: {journal}, Impact: {data['impact']}, Number of publications: {len(data['ids'])}")
    print('-----------------------------------------------')

    _tools = {'y': [], 'x': []}
    _publications = {'y': [], 'x': []}
    citations = {'y': [], 'x': []}

    for journal, data in top_journals:
        _publications['x'].append(journal)
        _publications['y'].append(len(data['ids']))

        # count each tool at most once per journal
        n_tools = 0
        pub_ids_set = set(data['ids'])
        for entry in tools:
            pubs = (entry.get('data') or {}).get("publication", []) or []
            # if any publication of this tool is in the set, count it once
            found = False
            for p in pubs:
                oid = _to_oid(p)
                if oid and oid in pub_ids_set:
                    found = True
                    break
            if found:
                n_tools += 1

        _tools['x'].append(journal)
        _tools['y'].append(n_tools)

        citations['x'].append(journal)
        citations['y'].append(data['impact'])

    result = {
        'variable': 'publications_journals_IF',
        'version': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'data': {'tools': _tools, 'publications': _publications, 'citations': citations},
        'collection': collection
    }
    mongo_adapter.insert_one("computationsDev", result)

    tools_w_pubs = sum(1 for t in tools if (t.get('data') or {}).get('publication'))
    denom = len(tools) or 1
    result_count = {
        'variable': 'publications_coverage',
        'version': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'data': {'count': tools_w_pubs, 'percentage': tools_w_pubs / denom},
        'collection': collection
    }
    mongo_adapter.insert_one("computationsDev", result_count)