import json
from collections import defaultdict
from urllib.parse import urlparse

def normalize_url(url):
    """Normalize a URL by removing the protocol, trailing slash, query parameters, and handling Bioconductor package URLs."""
    if not url:
        return None

    parsed_url = urlparse(url)
    netloc = parsed_url.netloc.lower()
    path = parsed_url.path.rstrip('/')

    # Remove query parameters and fragments
    path = path.split('?')[0].split('#')[0]

    # Remove '.html' from the end of Bioconductor URLs
    if path.endswith('.html'):
        path = path[:-5]

    # Handle Bioconductor package URLs
    if 'bioconductor.org' in netloc:
        parts = path.split('/')
        for part in reversed(parts):
            if part and part not in ('release', 'bioc', 'html', 'packages'):
                return f"bioconductor.org/packages/{part}"

    return f"{netloc}{path}"

def find_shared_links_across_groups(data):
    """
    Identify links that are shared by entries in different groups.
    
    Args:
        data (dict): The input data containing software entries grouped by key.
        
    Returns:
        dict: A dictionary where keys are shared links and values are lists of group_keys they appear in.
    """
    link_to_groups = defaultdict(set)

    # Map links to the groups they belong to
    for group_key, group_data in data.items():
        instances = group_data.get("instances", [])

        for instance in instances:
            repo_links = {normalize_url(repo["url"]) for repo in instance["data"].get("repository", []) if repo.get("url")}
            webpage_links = {normalize_url(url) for url in instance["data"].get("webpage", []) if url}
            combined_links = repo_links | webpage_links  # Union of both sets

            # Assign each link to its corresponding group key
            for link in combined_links:
                if link:  # Avoid adding None values
                    link_to_groups[link].add(group_key)

    # Filter only links that appear in multiple groups
    shared_links = {link: sorted(list(groups)) for link, groups in link_to_groups.items() if len(groups) > 1}

    return shared_links

if __name__ == "__main__":
    input_file = "data/grouped.json"
    output_file = "data/shared_links.json"
    
    # Load the input data
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Find links that are shared across different groups
    shared_links = find_shared_links_across_groups(data)
    # tools under shared/links must be grouped

    print(f"Found {len(shared_links)} links shared across multiple groups.")
    
    # Save the result to a JSON file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(shared_links, f, indent=4)
    
    print(f"Shared links have been saved to {output_file}.")
