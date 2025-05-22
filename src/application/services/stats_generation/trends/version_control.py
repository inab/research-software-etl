from datetime import datetime
from typing import List, Dict, Any
from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


'''
USAGE:
cursor = db.collection.find({})
version_control(cursor, collection="stats")
'''

def guess_repo_kind_from_url(url: str) -> str:
    if 'github.com' in url:
        return 'github'
    elif 'bitbucket.org' in url:
        return 'bitbucket'
    elif 'sourceforge.net' in url:
        return 'sourceforge'
    elif 'gitlab.com' in url:
        return 'gitlab'
    elif 'anaconda.org/bioconda' in url:
        return 'bioconda'
    elif 'git.bioconductor.org' in url:
        return 'bioconductor'
    return None


def version_control(tools: List[Dict[str, Any]], collection: str):
    # Counters
    repo_counts = {
        'github': 0,
        'gitlab': 0,
        'bitbucket': 0,
        'sourceforge': 0,
    }
    tools_with_repo = 0
    tools_without_repo = 0

    for entry in tools:
        entry = entry.get('data', {})
        links = set()

        # Collect repository URLs
        for repo in entry.get('repository', []):
            url = repo.get('url')
            if url:
                links.add(url)

        # Collect other links
        for link in entry.get('links', []):
            if link:
                links.add(link)

        found_repo = False
        found_types = set()

        for link in links:
            kind = guess_repo_kind_from_url(link)
            if kind in repo_counts:
                repo_counts[kind] += 1
                found_types.add(kind)
                found_repo = True

        if found_repo:
            tools_with_repo += 1
        else:
            tools_without_repo += 1

    # --- Output 1: version control presence ---
    data_count = {
        'version control': tools_with_repo,
        'no version control': tools_without_repo,
    }

    data_vs_count = {
        'variable': 'version_control_count',
        'version': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'data': data_count,
        'collection': collection
    }
    
    mongo_adapter.insert_one("computationsDev", data_vs_count)

    # --- Output 2: repository type distribution ---
    data_vs_repos = {
        'variable': 'version_control_repositories',
        'version': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'data': repo_counts,
        'collection': collection
    }
   
    mongo_adapter.insert_one("computationsDev", data_vs_repos)