import re
from collections import defaultdict
from urllib.parse import urlparse


# -----------------------------------------------------------------------------
# NORMALIZATION HELPERS
# -----------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    """
    Normalize software name for grouping/recovery.

    Rules:
    - None -> ""
    - lowercase
    - remove spaces, hyphens, underscores
    """
    if not name:
        return ""
    name = str(name).strip().lower()
    name = re.sub(r"[\s\-_]+", "", name)
    return name


def normalize_type(raw_type) -> str:
    """
    Normalize type.

    Rules:
    - None -> "*"
    - empty -> "*"
    - undefined -> "*"
    """
    if raw_type is None:
        return "*"

    t = str(raw_type).strip().lower()
    if not t or t == "undefined":
        return "*"

    return t


def normalize_source_stem_from_id(instance_id: str) -> str | None:
    """
    Extract a stable source stem from an instance id.

    Examples:
    - biotools/ms-digest/web/None -> biotools/ms-digest
    - bioconda_recipes/gdsctools/cmd/1.0.1 -> bioconda_recipes/gdsctools
    - galaxy/rnasnp/cmd/1.2.0 -> galaxy/rnasnp
    """
    if not instance_id:
        return None

    parts = [p.strip().lower() for p in str(instance_id).split("/") if p.strip()]
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return None


def normalize_url(url):
    """
    Normalize a URL so equivalent links can match.

    Rules:
    - accept missing scheme by assuming https
    - lowercase domain
    - remove trailing slash
    - remove query and fragment
    - remove final .html
    - canonicalize Bioconductor package URLs
    """
    if not url or not isinstance(url, str):
        return None

    url = url.strip()
    if not url:
        return None

    if "://" not in url and not url.startswith("//"):
        url = f"https://{url}"

    parsed_url = urlparse(url)
    netloc = parsed_url.netloc.lower().strip()
    path = parsed_url.path.rstrip("/")

    path = path.split("?")[0].split("#")[0]

    if not netloc:
        return None

    if path.endswith(".html"):
        path = path[:-5]

    if "bioconductor.org" in netloc:
        parts = [p for p in path.split("/") if p]
        for part in reversed(parts):
            if part and part not in ("release", "bioc", "html", "packages"):
                return f"bioconductor.org/packages/{part}"

    return f"{netloc}{path}".lower()


# -----------------------------------------------------------------------------
# GROUP INTROSPECTION
# -----------------------------------------------------------------------------

def get_group_identity(group_data: dict) -> tuple[set[str], set[str], set[str]]:
    """
    Return:
    - normalized names found in the group's instances
    - normalized source stems found in the group's instances
    - normalized types found in the group's instances
    """
    names = set()
    source_stems = set()
    types = set()

    for instance in group_data.get("instances", []):
        data = instance.get("data", {})

        name = normalize_name(data.get("name"))
        if name:
            names.add(name)

        inst_id = instance.get("_id")
        stem = normalize_source_stem_from_id(inst_id)
        if stem:
            source_stems.add(stem)

        types.add(normalize_type(data.get("type")))

    return names, source_stems, types


def get_group_links(group_data: dict) -> set[str]:
    """
    Extract normalized repository + webpage links from a group.
    """
    links = set()

    for instance in group_data.get("instances", []):
        data = instance.get("data", {})

        for repo in data.get("repository", []) or []:
            if isinstance(repo, dict):
                url = repo.get("url")
                normalized = normalize_url(url)
                if normalized:
                    links.add(normalized)

        for webpage in data.get("webpage", []) or []:
            normalized = normalize_url(webpage)
            if normalized:
                links.add(normalized)

    return links


# -----------------------------------------------------------------------------
# RECOVERY CANDIDATE DISCOVERY
# -----------------------------------------------------------------------------

def find_shared_links_across_groups(grouped_instancies):
    """
    Identify links shared by more than one group.

    Returns:
        {
            normalized_link: [group_key1, group_key2, ...]
        }
    """
    link_to_groups = defaultdict(set)

    for group_key, group_data in grouped_instancies.items():
        for link in get_group_links(group_data):
            link_to_groups[link].add(group_key)

    return {
        link: sorted(groups)
        for link, groups in link_to_groups.items()
        if len(groups) > 1
    }


def find_same_name_link_groups(shared_links, grouped_instancies):
    """
    Recover groups that:
    - share a normalized link
    - and have exactly one same normalized name across the candidate groups

    Type differences are ignored.
    """
    candidate_groups = []

    for _, group_keys in shared_links.items():
        all_names = set()
        valid = True

        for group_key in group_keys:
            group_data = grouped_instancies.get(group_key)
            if not group_data:
                valid = False
                break

            names, _, _ = get_group_identity(group_data)

            # Conservative: each group should internally correspond to one name
            if len(names) != 1:
                valid = False
                break

            all_names.update(names)

        if valid and len(all_names) == 1:
            candidate_groups.append(sorted(group_keys))

    return candidate_groups


def find_same_source_name_groups(grouped_instancies):
    """
    Recover groups that:
    - share the same normalized source stem
    - share the same normalized name
    - regardless of type
    """
    groups_by_identity = defaultdict(list)

    for group_key, group_data in grouped_instancies.items():
        names, source_stems, _ = get_group_identity(group_data)

        # Conservative: only recover groups that are internally coherent
        if len(names) != 1 or len(source_stems) != 1:
            continue

        identity = (next(iter(names)), next(iter(source_stems)))
        groups_by_identity[identity].append(group_key)

    return [
        sorted(group_keys)
        for group_keys in groups_by_identity.values()
        if len(group_keys) > 1
    ]


# -----------------------------------------------------------------------------
# MERGING OF OVERLAPPING RECOVERY GROUPS
# -----------------------------------------------------------------------------

def merge_overlapping_groups(groups):
    """
    Merge overlapping lists of group keys.

    Example:
    [['a', 'b'], ['b', 'c'], ['x', 'y']]
    ->
    [['a', 'b', 'c'], ['x', 'y']]
    """
    merged = []

    for group in groups:
        current = set(group)
        new_merged = []

        for existing in merged:
            if current & existing:
                current |= existing
            else:
                new_merged.append(existing)

        new_merged.append(current)
        merged = new_merged

    return [sorted(list(g)) for g in merged]


# -----------------------------------------------------------------------------
# GROUP UPDATE
# -----------------------------------------------------------------------------

def create_new_group_key(group, grouped_instancies):
    """
    Build merged key as name/type or name/* based on actual instance content.
    """
    all_names = set()
    all_types = set()

    for key in group:
        names, _, types = get_group_identity(grouped_instancies[key])
        all_names.update(names)
        all_types.update(types)

    name = min(all_names, key=len) if all_names else group[0].split("/")[0]

    if len(all_types) == 1 and "*" not in all_types:
        return f"{name}/{next(iter(all_types))}"

    return f"{name}/*"


def update_groups(groups_to_merge, grouped_instancies):
    """
    Merge the provided groups into new recovered groups.
    """
    for group in groups_to_merge:
        new_group_key = create_new_group_key(group, grouped_instancies)

        new_group_instances = []
        for key in group:
            new_group_instances.extend(grouped_instancies[key]["instances"])

        for key in group:
            del grouped_instancies[key]

        grouped_instancies[new_group_key] = {"instances": new_group_instances}

    return grouped_instancies


# -----------------------------------------------------------------------------
# DEBUG
# -----------------------------------------------------------------------------

def debug_group_links(grouped_instancies, target_keys):
    for group_key in target_keys:
        print(f"\nGROUP: {group_key}")
        group = grouped_instancies.get(group_key)
        if not group:
            print("  NOT FOUND")
            continue

        all_links = set()

        for instance in group.get("instances", []):
            repo_links = {
                normalize_url(repo["url"])
                for repo in instance.get("data", {}).get("repository", [])
                if isinstance(repo, dict) and repo.get("url")
            }
            webpage_links = {
                normalize_url(url)
                for url in instance.get("data", {}).get("webpage", [])
                if url
            }

            print("  raw repository:", instance.get("data", {}).get("repository"))
            print("  raw webpage:", instance.get("data", {}).get("webpage"))
            print("  normalized repository:", repo_links)
            print("  normalized webpage:", webpage_links)

            all_links.update(x for x in repo_links | webpage_links if x)

        print("  ALL LINKS:", sorted(all_links))


# -----------------------------------------------------------------------------
# MAIN RECOVERY
# -----------------------------------------------------------------------------

def recover_shared_name_link(grouped_instancies):
    """
    Recover split groups using two rules:

    1. Same source stem + same normalized name => merge regardless of type
    2. Shared normalized link + same normalized name => merge regardless of type

    Overlapping candidate groups are merged transitively.
    """
    print(f"Groups of tools before recovery: {len(grouped_instancies)}")
    print(f"Example of group keys: {list(grouped_instancies.keys())[:5]}")
    if grouped_instancies:
        example_key = list(grouped_instancies.keys())[0]
        print(f"Example of group data: {grouped_instancies[example_key]}")

    # Rule 1: same source + same name
    source_name_groups = find_same_source_name_groups(grouped_instancies)
    print(f"Groups recoverable by same source+name: {len(source_name_groups)}")
    print(f"Example source+name groups: {source_name_groups[:5]}")

    # Rule 2: shared link + same name
    shared_links = find_shared_links_across_groups(grouped_instancies)
    link_name_groups = find_same_name_link_groups(shared_links, grouped_instancies)
    print(f"Groups recoverable by shared link+name: {len(link_name_groups)}")
    print(f"Example link+name groups: {link_name_groups[:5]}")

    # Combine both recovery sources
    all_candidate_groups = source_name_groups + link_name_groups
    merged_candidate_groups = merge_overlapping_groups(all_candidate_groups)

    print(f"Total candidate groups before overlap merge: {len(all_candidate_groups)}")
    print(f"Total candidate groups after overlap merge: {len(merged_candidate_groups)}")
    print(f"Example merged candidate groups: {merged_candidate_groups[:5]}")

    if not merged_candidate_groups:
        print("No recoverable groups found.")
        return grouped_instancies

    grouped_instancies = update_groups(merged_candidate_groups, grouped_instancies)

    print(f"Groups of tools after recovery: {len(grouped_instancies)}")
    return grouped_instancies


if __name__ == "__main__":
    pass