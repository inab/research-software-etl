from collections import defaultdict
import pymongo
import os
import json
import logging
from dotenv import load_dotenv
from bson import json_util
from urllib.parse import urlparse



# Load environment variables
load_dotenv()

# =========================
# Unified grouping function with wildcard handling
# =========================

def normalize_url(url):
    """Normalize a URL by removing the protocol, trailing slash, and handling Bioconductor package URLs."""
    if not url:
        return None

    parsed_url = urlparse(url)
    netloc = parsed_url.netloc.lower()
    path = parsed_url.path.rstrip('/')  # Remove trailing slash
    
    # Remove '.html' from the end of Bioconductor URLs
    if path.endswith('.html'):
        path = path[:-5]

    # Handle Bioconductor package URLs
    if 'bioconductor.org' in netloc:
        parts = path.split('/')
        # Identify package name (last meaningful part)
        for part in reversed(parts):
            if part and part not in ('release', 'bioc', 'html', 'packages'):
                return f"bioconductor.org/packages/{part}"
    
    # Generic normalization: remove protocol, keep domain + path
    return f"{netloc}{path}"

def group_by_key_with_links(instances):
    """ Groups software entries based on shared repository links & name/type.
        - Uses a Union-Find method to ensure all linked entries are grouped together.
    """
    grouped_instances = {}
    link_to_keys = defaultdict(set)  # Map repository links to grouped keys
    name_type_to_key = {}  # Map name/type to a consistent key
    key_to_main_key = {}  # Tracks main key for merging groups

    def find_main_key(k):
        """Find the main key for a given entry (Union-Find approach)."""
        while key_to_main_key.get(k, k) != k:
            k = key_to_main_key[k]
        return k

    for inst in instances:
        name = inst['data']['name'].lower()
        software_type = inst['data'].get('type') or '*'  # Treat None as wildcard "*"

        if software_type == 'undefined':
            software_type = '*'

        key = f"{name}/{software_type}"

        # Extract repository and webpage links
        links = set()
        for repo in inst['data'].get('repository', []):
            if repo.get('url'):
                normalized_url = normalize_url(repo['url'])
                if normalized_url:
                    links.add(normalized_url)

        repository_links = ["github","sourceforge","gitlab","bitbucket", "bioconductor.org/packages", "pypi.org/project/", "metacpan.org/pod/", "cran.r-project.org/package"]
        if inst['data'].get('webpage'):
            for web_link in inst['data']['webpage']:
                normalized_url = normalize_url(web_link)
                if normalized_url and any(repo_link in normalized_url for repo_link in repository_links):
                    links.add(normalized_url)

        # Find existing groups that share links
        matching_keys = set()
        for link in links:
            if link in link_to_keys:
                matching_keys.update(link_to_keys[link])

        if key in name_type_to_key:
            matching_keys.add(name_type_to_key[key])

        if matching_keys:
            # Merge into the main existing group
            main_key = find_main_key(next(iter(matching_keys)))

            if main_key not in grouped_instances:
                grouped_instances[main_key] = {"instances": [], "links": set()}

            grouped_instances[main_key]['instances'].append(inst)
            grouped_instances[main_key]['links'].update(links)

            # Ensure match exists before trying to pop it
            for match in matching_keys:
                if match in grouped_instances and match != main_key:
                    grouped_instances[main_key]['instances'].extend(grouped_instances[match]['instances'])
                    grouped_instances[main_key]['links'].update(grouped_instances[match]['links'])
                    del grouped_instances[match]  # Safe deletion

                key_to_main_key[match] = main_key  # Merge identifiers

            for link in links:
                link_to_keys[link].add(main_key)

            name_type_to_key[key] = main_key

        else:
            # Create a new group
            grouped_instances[key] = {"instances": [inst], "links": links}
            for link in links:
                link_to_keys[link].add(key)
            name_type_to_key[key] = key
            key_to_main_key[key] = key  # Initialize root

    return grouped_instances


