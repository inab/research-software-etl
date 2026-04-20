import json
from disambiguate_oi import disambiguate_entries, build_prompt
import tiktoken
from urllib.parse import urlparse


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


def process_description(description):
    """Concatenates description items into a single string."""
    return " ".join(description) if description else ""


def find_disconnected_entries(data):
    """
    Identify cases where instances grouped under the same key do not share any repository or webpage link,
    but only consider instances that have at least one link and skip single-instance keys.
    
    Args:
        data (dict): The input data containing software entries.
        
    Returns:
        dict: A dictionary with keys where conflicts are found, containing both disconnected instances and remaining ones.
    """
    disconnected_keys = {}

    for key, value in data.items():
        instances = value.get("instances", [])

        # Collect all repository and webpage links per instance
        instance_links = []
        instance_details = []
        for instance in instances:
            repo_links = {normalize_url(repo["url"]) for repo in instance["data"].get("repository", []) if repo.get("url")}
            webpage_links = {normalize_url(url) for url in instance["data"].get("webpage", []) if url}
            combined_links = repo_links | webpage_links

            # Skip instances that have no links
            if not combined_links:
                continue

            instance_details.append({
                "name": instance["data"]["name"],
                "types": instance["data"].get("type", []),  # Support multiple types
                "source": instance["data"].get("source", []),
                "description": process_description(instance["data"].get("description", [])),
                "repository": list(repo_links),
                "webpage": list(webpage_links),
                "id": instance["_id"]
            })

            instance_links.append(combined_links)

        # Skip if only one valid instance remains (not conflictive)
        if len(instance_details) <= 1:
            continue

        # Check if there is any instance without a shared link with any other instance
        disconnected = []
        remaining = []
        for i, (details, links_a) in enumerate(zip(instance_details, instance_links)):
            shared = any(links_a & links_b for j, links_b in enumerate(instance_links) if i != j)
            if not shared:
                disconnected.append(details)
            else:
                remaining.append(details)

        if disconnected:
            disconnected_keys[key] = {
                "disconnected": disconnected,
                "remaining": remaining
            }

    return disconnected_keys


def build_instances_keys_dict(data):
    """Create a mapping of instance IDs to their respective instance data."""
    instances_keys = {}
    for key, value in data.items():
        instances = value.get("instances", [])
        for instance in instances:
            instances_keys[instance["_id"]] = instance
    return instances_keys


def token_size(text):
    """Estimate token size using tiktoken encoding."""
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def detect_conflicts(input_file, output_file, instances_dictionary_file):
    with open(input_file, "r", encoding="utf-8") as f:
            data = json.load(f)

    instances_dict = build_instances_keys_dict(data)
    disconnected_entries = find_disconnected_entries(data)
    print(f"{len(disconnected_entries)} conflictive keys found.")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(disconnected_entries, f, indent=4)
    
    print(f'Disconnected entries saved to "{output_file}".')

    with open(instances_dictionary_file, "w", encoding="utf-8") as f:
        json.dump(instances_dict, f, indent=4)
    
    print(f'Instances dictionary saved to "{instances_dictionary_file}".')




if __name__ == "__main__":
    input_file = "data/grouped.json"
    output_file = "data/disconnected_entries.json"
    instances_dictionary_file = "data/instances_dict.json"

    detect_conflicts(input_file, output_file, instances_dictionary_file)

    

