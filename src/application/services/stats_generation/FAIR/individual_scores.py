from infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
from bson import ObjectId
from pprint import pprint
import requests 
from urllib.parse import urlparse


def get_pub(object_id):
    from infrastructure.db.mongo.mongo_db_singleton import mongo_adapter

    publication = mongo_adapter.fetch_entry( "publicationsMetadataDev", object_id)    
    if publication:
        return publication.get('data')
    else:
        return None



VERSION_CONTROL_DOMAINS = {
    "github.com",
    "gitlab.com",
    "bitbucket.org",
}


def _domain_from_url(url: str) -> str | None:
    """Extract and normalize the domain from a URL."""
    if not isinstance(url, str) or not url.strip():
        return None

    url = url.strip()

    # urlparse needs a scheme to reliably parse netloc
    if "://" not in url:
        url = "https://" + url

    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    # Remove credentials and port if present
    if "@" in domain:
        domain = domain.split("@", 1)[1]
    if ":" in domain:
        domain = domain.split(":", 1)[0]

    # Normalize www.github.com -> github.com
    if domain.startswith("www."):
        domain = domain[4:]

    return domain or None


def _is_version_control_url(url: str) -> bool:
    domain = _domain_from_url(url)
    return domain in VERSION_CONTROL_DOMAINS


def has_version_control(entry: dict) -> bool:
    """
    Return True if the entry contains at least one link, webpage,
    download, or repository URL hosted on a known version-control domain.
    """
    if not isinstance(entry, dict):
        return False

    # Simple URL lists
    for field in ("links", "webpage", "download"):
        values = entry.get(field, [])
        if not isinstance(values, list):
            continue

        for url in values:
            if _is_version_control_url(url):
                return True

    # Repository list of dicts
    repositories = entry.get("repository", [])
    if isinstance(repositories, list):
        for repo in repositories:
            if isinstance(repo, dict):
                if _is_version_control_url(repo.get("url")):
                    return True
            elif isinstance(repo, str):
                # In case some entries store repositories directly as strings
                if _is_version_control_url(repo):
                    return True

    return False

def request_fair_calculation(entry) -> None:
    
    URL ="https://observatory.openebench.bsc.es/api/fair/evaluate"
    #URL ="http://127.0.0.1:8000/fair/evaluate"
    body = {
        'tool_metadata': entry,
        "prepare": False
    }
    request = requests.post(URL, json=body)
    # request fair calculation
    if request.status_code == 200:
        result = request.json()
    else:
        print(f"Error: {request.status_code}")
        print(f"Error: {request.text}")
        print(entry)
        raise
        return None

    return result['result']



def collect_entry_links(entry: dict) -> list[str]:
    """
    Collect all relevant URLs from an entry into a single list.

    It supports:
    - source_code: list[str]
    - download: list[str]
    - repository: list[dict] with "url", or list[str]
    - source: list[str], adding source-level URLs for known sources
    """
    if not isinstance(entry, dict):
        return []

    collected_links = []

    # Direct URL fields
    for field in ("source_code", "download", "repository"):
        values = entry.get(field, [])

        if not isinstance(values, list):
            continue

        for item in values:
            if isinstance(item, str) and item.strip():
                collected_links.append(item.strip())

            elif isinstance(item, dict):
                url = item.get("url")
                if isinstance(url, str) and url.strip():
                    collected_links.append(url.strip())

    # Source-derived URLs
    source_url_map = {
        "bioconda_recipes": "https://bioconda.github.io/",
        "Bioconductor": "https://www.bioconductor.org/",
    }

    sources = entry.get("source", [])
    if isinstance(sources, list):
        for source in sources:
            if not isinstance(source, str):
                continue

            if source in source_url_map:
                collected_links.append(source_url_map[source])

    return collected_links



def prep_entry_for_evaluation(entry):

    publications_records = set()

    id = str(entry.get('_id'))
    entry = entry.get('data', {})
    publications_new = []
    if entry.get('publication'):
        for pub in entry['publication']:
            publication = get_pub(ObjectId(pub))
            if publication:
                publications_records.add(id)
                if 'citations' in publication:
                    del publication['citations']
                if 'abstract' in publication:
                    del publication['abstract']
            
                publications_new.append(publication)
        
    entry['publication'] = publications_new

    if entry.get('type'):
        if len(entry.get('type', []))>1:
            entry['other_types'] = entry.get('type', [])[1:]
            entry['type'] = entry.get('type', [])[0]
        else:
            entry['other_types'] = []
            entry['type'] = entry.get('type', [])[0]
    else:
        entry['type'] = None
        entry['other_types'] = []

    if entry.get('version'):
        if len(entry.get('version', []))>1:
            entry['other_versions'] = entry.get('version', [])[1:]
            entry['version'] = entry.get('version', [])[0]
        else:
            entry['other_versions'] = []
            entry['version'] = entry.get('version', [])[0]
    else:
        entry['version'] = None
        entry['other_versions'] = []


    if entry['authors'] is None:
        entry['authors'] = []
    else:
        for author in entry['authors']:
            if author['type'] == None:
                author['type'] = 'unknown'
            if author['name'] == None:
                author['name'] = 'unknown'
            if author['email'] == None:
                author['email'] = ''


    repos = []
    if entry['repository']:
        for repo in entry['repository']:
            if repo.get('url'):
                repos.append(repo['url'])
    entry['repository'] = repos

    if entry['test'] is True:
        entry['test'] = ['https://openebech.bsc.es']
    else:
        entry['test'] = []

    entry['src'] = collect_entry_links(entry)

    if entry['operating_system']:
        entry['os'] = entry['operating_system']
    else:
        entry['os'] = []


    entry['version_control'] = has_version_control(entry)

    return entry



def evaluate_tool(entry):
    from fairsoft_core.evaluation.all_indicators import run_fairsoft_evaluation 

    entry = prep_entry_for_evaluation(entry)

    #result = { id: request_fair_calculation(entry)}

    #result = request_fair_calculation(entry)

    result = run_fairsoft_evaluation(entry).get('result')


    return result

