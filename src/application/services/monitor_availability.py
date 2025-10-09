from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter
import requests

types = ['web', 'db', 'sparql', 'soap', 'rest', 'workbench', 'suite']

def check_url_availability(url):
    """
    Check if a URL is reachable.
    """
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False
    

def compute_url_availabilities_summary(entry):
    entries_types = {}
    for type in types:
        entries = mongo_adapter.fetch_entries("toolsDev", {'data.type': type})
        entries_types[type] = [entry["_id"] for entry in entries]
        n_total = 0
        n_available = 0
        n_unavailable = 0
        n_no_url = 0
        for entry in entries:
            n_total += 1
            entry = entry.get('data', {})
            entry['type'] = type
            URLs = entry.get('webpage')
            if not URLs:
                n_no_url += 1
            else:
                for URL in URLs:
                    if URL:
                        is_available = check_url_availability(URL)
                        if not is_available:
                            n_unavailable += 1
                        else:
                            n_available += 1
        
        print("----- Summary -----")
        print(f"Type: {type}")
        print(f"Total: {n_total}")
        print(f"No URL: {n_no_url}")
        print(f"Available: {n_available}")
        print(f"Unavailable: {n_unavailable}")



if __name__ == "__main__":
    entries_types = {}
    n_no_url = 0
    n_url = 0
    n_available = 0
    n_unavailable = 0

    for type in types:
        entries = mongo_adapter.fetch_entries("toolsDev", {'data.type': type})
        entries_types[type] = [entry["_id"] for entry in entries]
    
    # calculate total unique entries 
    unique_entries = set()
    for type in types:
        unique_entries.update(entries_types[type])
    
    n_total = len(unique_entries)

    for entry in unique_entries:
        entry = mongo_adapter.fetch_entry("toolsDev", entry)
        entry = entry.get('data', {})
        URLs = entry.get('webpage')
        if not URLs:
            n_no_url += 1
        else:
            for URL in URLs:
                if URL:
                    n_url += 1
                    is_available = check_url_availability(URL)
                    if not is_available:
                        n_unavailable += 1
                    else:
                        n_available += 1

    print("----- Summary -----")
    print(f"Total entries: {n_total}")
    print(f"No URL: {n_no_url}")
    print(f"URL: {n_url}")
    print(f"Available: {n_available}")
    print(f"Unavailable: {n_unavailable}")



        
        

