from datetime import datetime
from typing import List, Dict, Any
from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from collections import Counter
from collections import defaultdict

import re

# Helper functions
def is_downloadable(url):
    return bool(re.search(r'\.(pdf|md|rst|docx?|zip|tar\.gz|tgz)$', url, re.IGNORECASE))

def is_web(url):
    return bool(re.search(r'\.(html?|php)?$', url, re.IGNORECASE)) and not is_downloadable(url)

def detect_platform(url):
    if "github.com" in url:
        return "github"
    elif "gitlab.com" in url:
        return "gitlab"
    else:
        return None 

# Format keys
FORMAT_KEYS = ["web", "downloadable", "github", "gitlab", "total"]

def count_documentation(tools: List[Dict[str, Any]]):
    
    # Main dictionary with all format keys prefilled
    def new_format_counter():
        return {key: 0 for key in FORMAT_KEYS}

    doc_format_counts = defaultdict(new_format_counter)

    # Iterate over all documents
    tools_w_docs = 0
    for doc in tools:
        docs = doc.get("data", {}).get("documentation", [])
        if len(docs)>0:
            tools_w_docs += 1

        for entry in docs:
            doc_type = entry.get("type", "").strip().lower().replace("_", " ")
            url = entry.get("url", "")
            if not doc_type or not url:
                continue

            platforms = set()
            if is_downloadable(url):
                doc_format_counts[doc_type]["downloadable"] += 1
            else:
                doc_format_counts[doc_type]["web"] += 1  # default to web if not downloadable

            platform = detect_platform(url)
            if platform:
                doc_format_counts[doc_type][platform] += 1

            doc_format_counts[doc_type]["total"] += 1

    doc_format_counts = {k: dict(v) for k, v in doc_format_counts.items()}

    return doc_format_counts, tools_w_docs


def documentation_stats(doc_format_counts, collection):
    summary = {
        'variable': 'documentation',
        'version': datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'data': doc_format_counts,
        'collection': collection
    }

    return summary


def documentation_coverage(tools, tools_w_docs, collection):

    data = {
        'count': tools_w_docs,
        'percentage': tools_w_docs/len(list(tools))
    }

    doc = {
        'variable': 'documentation_coverage',
        'version': datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        'data': data,
        'collection': collection
    }

    return doc


def documentation(tools: List[Dict[str, Any]], collection: str):
    documentation_counts, tools_w_docs = count_documentation(tools)

    documentation_summary = documentation_stats(documentation_counts, collection)
    mongo_adapter.insert_one("computationsDev", documentation_summary)

    documentation_coverage_doc = documentation_coverage(tools, tools_w_docs, collection)
    mongo_adapter.insert_one("computationsDev", documentation_coverage_doc)


