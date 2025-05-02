import tiktoken
from urllib.parse import urlparse
import logging

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

def are_same_by_source_and_name(entry1, entry2):
    """Check if two entries have the same name and overlapping source."""
    name1 = entry1.get("name", "").strip().lower()
    name2 = entry2.get("name", "").strip().lower()
    sources1 = set(map(str.lower, entry1.get("source", [])))
    sources2 = set(map(str.lower, entry2.get("source", [])))
    return name1 == name2 and bool(sources1 & sources2)


def apply_source_name_merge(conflict_blocks):
    """
    For each conflict block, move disconnected entries to 'remaining'
    if they share source + name with any of the remaining entries.
    """
    updated = {}

    for key, block in conflict_blocks.items():
        disconnected = block.get("disconnected", [])
        remaining = block.get("remaining", [])

        merged = []
        still_disconnected = []

        for disc in disconnected:
            if any(are_same_by_source_and_name(disc, rem) for rem in remaining):
                merged.append(disc)
            else:
                still_disconnected.append(disc)

        if merged:
            print(f"🔗 Merging {len(merged)} disconnected entries into remaining for block: {key}")

        updated[key] = {
            "remaining": remaining + merged,
            "disconnected": still_disconnected
        }

    return updated

def is_galaxy_related(entry):
    sources = set(s.lower() for s in entry.get("source", []))
    return bool(sources & {"galaxy", "toolshed", "galaxy_metadata"})

def all_entries_same_name_and_galaxy_related(instance_details):
    if not instance_details:
        return False
    name_set = {e["name"].strip().lower() for e in instance_details}
    if len(name_set) != 1:
        return False
    for entry in instance_details:
        if not is_galaxy_related(entry):
            return False
    return True

def get_galaxy_related_same_name(entries):
    """Return all galaxy-related entries that share the same name (most common)."""
    name_counter = {}
    for e in entries:
        if is_galaxy_related(e):
            name = e["name"].strip().lower()
            name_counter[name] = name_counter.get(name, 0) + 1

    if not name_counter:
        return []

    # Get most common name among galaxy-related entries
    common_name = max(name_counter.items(), key=lambda x: x[1])[0]

    return [e for e in entries if is_galaxy_related(e) and e["name"].strip().lower() == common_name]


def find_disconnected_entries(data, use_name_match_for_no_links=True):
    """
    Identify conflicts based on link similarity and optionally use a heuristic
    that assumes no-link entries with the same name are the same software.
    
    Args:
        data (dict): grouped_entries or blocks dictionary
        use_name_match_for_no_links (bool): if True, treat no-link entries as 'remaining'
    
    Returns:
        dict: conflict_blocks with 'disconnected' and 'remaining' entries
    """
    disconnected_keys = {}

    for key, value in data.items():
        instances = value.get("instances", [])

        instance_links = []
        instance_details = []

        for instance in instances:
            sources = instance["data"].get("source", [])
    
            # 🚫 Skip open_metrics entries
            if any(s.lower() == "opeb_metrics" for s in sources):
                #logging.debug(f"Skipping entry {instance['_id']} due to source 'open_metrics'")
                continue

            if any(s.lower() == "bioconda" for s in sources):
                #logging.debug(f"Skipping entry {instance['_id']} due to source 'open_metrics'")
                continue

            repo_links = {normalize_url(repo["url"]) for repo in instance["data"].get("repository", []) if repo.get("url")}
            webpage_links = {normalize_url(url) for url in instance["data"].get("webpage", []) if url}
            combined_links = repo_links | webpage_links

            entry = {
                "name": instance["data"]["name"],
                "types": instance["data"].get("type", []),
                "source": instance["data"].get("source", []),
                "description": process_description(instance["data"].get("description", [])),
                "repository": list(repo_links),
                "webpage": list(webpage_links),
                "id": instance["_id"]
            }

            instance_details.append(entry)
            instance_links.append(combined_links)

        if len(instance_details) <= 1:
            continue

        if all_entries_same_name_and_galaxy_related(instance_details):
            logging.debug(f"Skipping conflict for {key} — all Galaxy-related entries with same name.")
            continue


        disconnected = []
        remaining = []

        for i, (details, links_a) in enumerate(zip(instance_details, instance_links)):
            if not links_a:
                if use_name_match_for_no_links or is_galaxy_related(details):
                    remaining.append(details)
                else:
                    disconnected.append(details)
            else:
                shared = any(links_a & links_b for j, links_b in enumerate(instance_links) if i != j)
                if not shared:
                    disconnected.append(details)
                else:
                    remaining.append(details)

        # Promote galaxy-related entries with common name to 'remaining'
        galaxy_group = get_galaxy_related_same_name(instance_details)

        if galaxy_group:
            galaxy_ids = {e["id"] for e in galaxy_group}
            # Remove them from disconnected if they were incorrectly flagged
            disconnected = [e for e in disconnected if e["id"] not in galaxy_ids]

            # Avoid duplicates in remaining
            existing_ids = {e["id"] for e in remaining}
            for g in galaxy_group:
                if g["id"] not in existing_ids:
                    remaining.append(g)

        if disconnected:
            disconnected_keys[key] = {
                "disconnected": disconnected,
                "remaining": remaining
            }

    return disconnected_keys




def token_size(text):
    """Estimate token size using tiktoken encoding."""
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))



if __name__ == "__main__":
    input_file = "data/grouped.json"
    output_file = "data/disconnected_entries.json"
    instances_dictionary_file = "data/instances_dict.json"

    find_disconnected_entries(input_file)

    

