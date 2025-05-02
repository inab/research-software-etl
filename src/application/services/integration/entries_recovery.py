import json
from collections import defaultdict
from urllib.parse import urlparse

# Merges groups with shared links and same name and updated the grouped.json file

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


def find_shared_links_accross_groups(data):
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


def find_same_name_link_groups(shared_links):
    unique_name_groups = []
    for link in shared_links:
        unique_names = set()
        for tool in shared_links[link]:
            name = tool.split('/')[0]
            unique_names.add(name)

        if len(unique_names) == 1:
            unique_name_groups.append(shared_links[link])

    return unique_name_groups


def create_new_group_key(group):
    # The new key has the format: "name/*". If there is only one type, the key is "name/type"
    name = group[0].split('/')[0]
    types = set([tool.split('/')[1] for tool in group])
    if len(types) == 1 and "*" not in types:
        return f"{name}/{types.pop()}"
    else:
        return f"{name}/*"


def update_groups(unique_name_groups, grouped_instancies):
    # 1. Add the new merged groups (new merged key and full instances as values) and remove the original groups
    seen_keys = set()
    seen_groups = []
    for group in unique_name_groups:
        if group in seen_groups:
            print(f"Group {group} already seen")
        # 1.1. Create a new key for the merged group
        new_group_key = create_new_group_key(group)
        # 1.2. Create a new group with the full instances
        new_group_instances = []
        for key in group:
            if key not in seen_keys:
                seen_keys.add(key)
            else:
                print(f"Key {key} already seen")
                print(f"group: {group}")
            new_group_instances.extend(grouped_instancies[key]["instances"])

        # 1.3 remove the original groups from the grouped_instancies. 
        # This is doen before the addition of the new group to avoid conflicts with the new key
        for key in group:
            del grouped_instancies[key]

        # 1.4. Add the new group to the new dictionary
        grouped_instancies[new_group_key] = {"instances": new_group_instances}

        seen_groups.append(group)

    return grouped_instancies


def recover_shared_name_link(grouped_instancies):    

    print(f"Groups of tools before recovery: {len(grouped_instancies)}")
    print(f"Example of group keys: {list(grouped_instancies.keys())[:5]}")
    example_key = list(grouped_instancies.keys())[0]
    print(f"Example of group data: {grouped_instancies[example_key]}")

    # 1. Build the shared_links dictionary
    shared_links = find_shared_links_accross_groups(grouped_instancies)

    # 2. Find same name and link occurrencies
    unique_name_groups = find_same_name_link_groups(shared_links)

    print(f"Groups of tools with same name and common link: {len(unique_name_groups)}")
    print(f"Example of groups: {unique_name_groups[:5]}")

    # 3. Merge groups with same name and shared links and add to the grouped_instances dictionary

    # check wether any key appears in more than one group 
    
    keys_in_several_groups = []
    for key in grouped_instancies:
        count = 0
        for group in unique_name_groups:
            if key in group:
                count += 1
        if count > 1:
            keys_in_several_groups.append(key)
    
    print(f"Keys in more than one group: {len(set(keys_in_several_groups))}")
    print(f"Keys: {keys_in_several_groups}")

    # the groups containing the same keys must be merged
    merged_groups = []
    groups_to_remove = []
    for key in keys_in_several_groups:
        new_group = []
        for group in unique_name_groups:
            if key in group:
                groups_to_remove.append(group)
                if key not in new_group:
                    new_group.extend(group)
                    print(f"To remove: {group}")
        if new_group not in merged_groups:
            merged_groups.append(new_group)
            print(f"To merge: {new_group}")
    

    print(f"Groups merged: {len(groups_to_remove)}")
    print(groups_to_remove)
    print(f"Groups to be merged: {len(merged_groups)}")
    print(merged_groups)

    # Update the unique_name_groups list
    new_unique_names_groups = []
    count = 0
    for group in unique_name_groups:
        if group not in groups_to_remove:
            new_unique_names_groups.append(group)
        else:
            print(f"Removing group: {group}")
            count += 1
    
    print(f"Groups removed: {count}")
    
    print(f"Groups without the merged groups: {len(new_unique_names_groups)}")

    for group in merged_groups:
        new_unique_names_groups.append(group)  
     
    print(f"Groups of tools with same name and common link after merging: {len(new_unique_names_groups)}")
    print(f"Example of groups: {unique_name_groups[:5]}")

    
    grouped_instancies = update_groups(new_unique_names_groups, grouped_instancies)
    print(f"Groups of tools after recovery: {len(grouped_instancies)}")

    return grouped_instancies





if __name__ == "__main__":
    pass
