import logging
import re
import tiktoken
import requests
from urllib.parse import urlparse

_GITHUB_RESOLUTION_CACHE = {}

# Reuse a session for efficiency
_HTTP_SESSION = requests.Session()
_HTTP_SESSION.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (compatible; conflict-detector/1.0)"
    }
)


def ensure_url_has_scheme(url: str) -> str:
    """
    Add https:// if the URL has no scheme.

    Examples:
    - github.com/bcgsc/AMPd-Up -> https://github.com/bcgsc/AMPd-Up
    - www.github.com/foo/bar -> https://www.github.com/foo/bar
    - https://github.com/foo/bar -> unchanged
    """
    if not url:
        return url

    url = url.strip()
    if not url:
        return url

    parsed = urlparse(url)
    if parsed.scheme:
        return url

    return f"https://{url}"


def normalize_url(url):
    """
    Cheap normalization only.
    No network calls here.

    Rules:
    - add scheme if missing (for correct parsing)
    - remove protocol
    - lowercase domain
    - remove trailing slash
    - remove final .git
    - canonicalize GitHub URLs to github.com/owner/repo
    - canonicalize Bioconductor package URLs
    """
    if not url:
        return None

    url = url.strip()
    if not url:
        return None

    url = ensure_url_has_scheme(url)
    parsed_url = urlparse(url)

    netloc = parsed_url.netloc.lower().strip()
    path = parsed_url.path.rstrip("/").strip().lower()

    if not netloc:
        return None

    # Remove final .git
    if path.endswith(".git"):
        path = path[:-4]

    # GitHub canonicalization: keep only owner/repo if possible
    if netloc in {"github.com", "www.github.com"}:
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2:
            owner = parts[0]
            repo = parts[1]
            if repo.endswith(".git"):
                repo = repo[:-4]
            return f"github.com/{owner}/{repo}"
        return "github.com"

    # Remove .html from end
    if path.endswith(".html"):
        path = path[:-5]

    # Bioconductor canonicalization
    if "bioconductor.org" in netloc:
        parts = [p for p in path.split("/") if p]
        for part in reversed(parts):
            if part and part not in {"release", "bioc", "html", "packages"}:
                return f"bioconductor.org/packages/{part}"

    normalized = f"{netloc}{path}"
    return normalized if normalized else None


def is_github_url(url):
    """
    Return True for GitHub URLs, including scheme-less ones like github.com/foo/bar.
    """
    if not url:
        return False

    try:
        parsed = urlparse(ensure_url_has_scheme(url))
        return parsed.netloc.lower() in {"github.com", "www.github.com"}
    except Exception:
        return False


def resolve_github_url(url, timeout=8):
    """
    Resolve redirects for a GitHub URL.
    Returns the final URL as returned by requests, or None if resolution failed
    or if the resolved target normalizes to the same repo.

    Important:
    - works with scheme-less input
    - tries HEAD first, then GET as fallback
    - caches both positive and negative results
    """
    if not url or not is_github_url(url):
        return None

    original_input = url.strip()
    if original_input in _GITHUB_RESOLUTION_CACHE:
        return _GITHUB_RESOLUTION_CACHE[original_input]

    request_url = ensure_url_has_scheme(original_input)

    try:
        # First try HEAD
        response = _HTTP_SESSION.head(request_url, allow_redirects=True, timeout=timeout)
        final_url = response.url

        # Some servers are not reliable with HEAD; fallback to GET if needed
        if not final_url:
            response = _HTTP_SESSION.get(
                request_url,
                allow_redirects=True,
                timeout=timeout,
                stream=True,
            )
            final_url = response.url

        # Compare normalized forms, not raw strings
        original_norm = normalize_url(original_input)
        final_norm = normalize_url(final_url)

        if final_url and final_norm and final_norm != original_norm:
            _GITHUB_RESOLUTION_CACHE[original_input] = final_url
            return final_url

    except requests.RequestException as e:
        logging.debug(f"Could not resolve GitHub URL {original_input}: {e}")

    _GITHUB_RESOLUTION_CACHE[original_input] = None
    return None


def get_normalized_link_variants(url, resolve_github=False):
    """
    Return normalized link variants for a URL.

    Always includes the normalized original URL.
    Optionally includes the normalized resolved GitHub target URL.
    """
    variants = set()

    normalized_original = normalize_url(url)
    if normalized_original:
        variants.add(normalized_original)

    if resolve_github and is_github_url(url):
        resolved = resolve_github_url(url)
        if resolved:
            normalized_resolved = normalize_url(resolved)
            if normalized_resolved:
                variants.add(normalized_resolved)

    return variants


def collect_link_set(urls, resolve_github=False):
    collected = set()
    for url in urls:
        if url:
            collected |= get_normalized_link_variants(url, resolve_github=resolve_github)
    return collected


def process_description(description):
    return " ".join(description) if description else ""



def normalize_source_identity(source: str) -> str | None:
    """
    Normalize a source string to a stable identity suitable for conflict-block merging.

    Examples:
    - bioconda_recipes/perl-datetime/lib/1.59 -> bioconda_recipes/perl-datetime
    - bioconda/perl-datetime/lib/1.59 -> bioconda/perl-datetime
    - biotools/peptideshaker/app/1.16.45 -> biotools/peptideshaker
    - galaxy/foo -> galaxy/foo
    """
    if not source:
        return None

    parts = [p.strip().lower() for p in source.split("/") if p.strip()]
    if not parts:
        return None

    if parts[0] == "bioconda_recipes" and len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"

    if parts[0] == "bioconda" and len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"

    if parts[0] == "biotools" and len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"

    if parts[0] == "toolshed" and len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"

    if parts[0] == "galaxy" and len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"

    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"

    return parts[0]


def get_normalized_source_identities(entry):
    identities = set()

    generic_sources = {
        "biotools",
        "github",
        "sourceforge",
        "bioconductor",
        "bioconda",
        "bioconda_recipes",
        "galaxy",
        "toolshed",
        "galaxy_metadata",
        "oeb_metrics",
    }

    for source in entry.get("source", []):
        normalized = normalize_source_identity(source)
        if normalized and normalized not in generic_sources:
            identities.add(normalized)

    entry_id = entry.get("id")
    normalized_id = normalize_source_identity(entry_id)
    if normalized_id:
        identities.add(normalized_id)

    return identities


def normalize_name_strict(name: str) -> str:
    if not name:
        return ""
    return " ".join(name.strip().lower().split())


def normalize_name_relaxed(name: str) -> str:
    if not name:
        return ""
    name = name.strip().lower()
    name = re.sub(r"[_\-]+", " ", name)
    name = re.sub(r"\s+", " ", name)
    return name

def get_source_origins(entry):
    origins = set()

    for source in entry.get("source", []):
        if not source:
            continue
        parts = [p.strip().lower() for p in source.split("/") if p.strip()]
        if parts:
            origins.add(parts[0])

    entry_id = entry.get("id")
    if entry_id:
        parts = [p.strip().lower() for p in entry_id.split("/") if p.strip()]
        if parts:
            origins.add(parts[0])

    return origins


def share_source_origin(entry1, entry2):
    return bool(get_source_origins(entry1) & get_source_origins(entry2))


def are_same_by_source_and_name(entry1, entry2):
    """
    Two entries are considered the same for conflict resolution if:
    - their names match under the appropriate comparison rule
    - and either:
        * both are Galaxy-related
        * or they share a normalized source identity
    """

    same_origin = share_source_origin(entry1, entry2)

    if same_origin:
        # Within the same source, be conservative:
        # different names may indicate a real conflict.
        name1 = normalize_name_strict(entry1.get("name", ""))
        name2 = normalize_name_strict(entry2.get("name", ""))
    else:
        # Across different sources, allow formatting variants.
        name1 = normalize_name_relaxed(entry1.get("name", ""))
        name2 = normalize_name_relaxed(entry2.get("name", ""))

    if name1 != name2:
        return False

    if is_galaxy_related(entry1) and is_galaxy_related(entry2):
        return True

    sources1 = get_normalized_source_identities(entry1)
    sources2 = get_normalized_source_identities(entry2)

    return bool(sources1 & sources2)


def resolve_source_name_clusters(conflict_blocks):
    """
    Post-process conflict blocks without undoing link-based grouping.

    Rules:
    - entries already in `remaining` stay there
    - a disconnected entry moves to remaining if it matches any remaining entry
    - disconnected entries that match each other form clusters; clusters of size > 1
      are also moved to remaining
    - only unresolved singletons remain in disconnected
    - fully resolved blocks are removed
    """
    updated = {}

    for key, block in conflict_blocks.items():
        remaining = list(block.get("remaining", []))
        disconnected = list(block.get("disconnected", []))

        existing_remaining_ids = {e["id"] for e in remaining}

        # First, pull into remaining any disconnected entries that match existing remaining
        promoted = []
        still_disconnected = []

        for disc in disconnected:
            if any(are_same_by_source_and_name(disc, rem) for rem in remaining):
                promoted.append(disc)
            else:
                still_disconnected.append(disc)

        if promoted:
            remaining.extend(promoted)
            existing_remaining_ids.update(e["id"] for e in promoted)

        # Then cluster the disconnected leftovers among themselves
        visited = set()
        clustered_remaining = []
        final_disconnected = []

        for i, entry in enumerate(still_disconnected):
            entry_id = entry["id"]
            if entry_id in visited:
                continue

            cluster = []
            stack = [i]

            while stack:
                idx = stack.pop()
                current = still_disconnected[idx]
                current_id = current["id"]

                if current_id in visited:
                    continue

                visited.add(current_id)
                cluster.append(current)

                for j, candidate in enumerate(still_disconnected):
                    candidate_id = candidate["id"]
                    if candidate_id in visited:
                        continue
                    if are_same_by_source_and_name(current, candidate):
                        stack.append(j)

            if len(cluster) > 1:
                clustered_remaining.extend(cluster)
            else:
                final_disconnected.extend(cluster)

        if clustered_remaining:
            remaining.extend(clustered_remaining)

        if final_disconnected:
            updated[key] = {
                "remaining": remaining,
                "disconnected": final_disconnected,
            }

    return updated


def all_entries_same_name_and_galaxy_related(instance_details):
    if not instance_details:
        return False
    name_set = {e["name"].strip().lower() for e in instance_details}
    if len(name_set) != 1:
        return False
    return all(is_galaxy_related(entry) for entry in instance_details)


def is_galaxy_related(entry):
    """
    Return True if the entry comes from a Galaxy-related source.
    Works with plain source names, full source ids, and entry ids.
    """
    identities = get_normalized_source_identities(entry)

    return any(
        identity == "galaxy"
        or identity == "toolshed"
        or identity == "galaxy_metadata"
        or identity.startswith("galaxy/")
        or identity.startswith("toolshed/")
        or identity.startswith("galaxy_metadata/")
        for identity in identities
    )


def get_galaxy_related_same_name(entries):
    """
    Return all galaxy-related entries whose name appears in at least
    two galaxy-related entries in the block.
    """
    name_counter = {}
    for e in entries:
        if is_galaxy_related(e):
            name = e["name"].strip().lower()
            name_counter[name] = name_counter.get(name, 0) + 1

    valid_names = {name for name, count in name_counter.items() if count >= 2}

    return [
        e for e in entries
        if is_galaxy_related(e) and e["name"].strip().lower() in valid_names
    ]




def build_instance_representation(instances, resolve_github=False):
    """
    Build instance_details and instance_links for one block.
    """
    instance_links = []
    instance_details = []

    for instance in instances:
        sources = instance["data"].get("source", [])

        if any(s.lower() == "opeb_metrics" for s in sources):
            continue

        if any(s.lower() == "bioconda" for s in sources):
            continue

        repo_urls = [
            repo["url"]
            for repo in instance["data"].get("repository", [])
            if repo.get("url")
        ]
        webpage_urls = [
            url
            for url in instance["data"].get("webpage", [])
            if url
        ]

        repo_links = collect_link_set(repo_urls, resolve_github=resolve_github)
        webpage_links = collect_link_set(webpage_urls, resolve_github=resolve_github)
        combined_links = repo_links | webpage_links

        entry = {
            "name": instance["data"]["name"],
            "types": instance["data"].get("type", []),
            "source": instance["data"].get("source", []),
            "description": process_description(instance["data"].get("description", [])),
            "repository": sorted(repo_links),
            "webpage": sorted(webpage_links),
            "id": instance["_id"],
        }

        instance_details.append(entry)
        instance_links.append(combined_links)

    return instance_details, instance_links


def classify_entries(instance_details, instance_links, use_name_match_for_no_links=True):
    """
    Classify entries into disconnected and remaining using already-built link sets.
    """
    disconnected = []
    remaining = []

    for i, (details, links_a) in enumerate(zip(instance_details, instance_links)):
        if not links_a:
            if use_name_match_for_no_links or is_galaxy_related(details):
                remaining.append(details)
            else:
                disconnected.append(details)
        else:
            shared = any(
                links_a & links_b
                for j, links_b in enumerate(instance_links)
                if i != j
            )
            if shared:
                remaining.append(details)
            else:
                disconnected.append(details)

    galaxy_group = get_galaxy_related_same_name(instance_details)

    if galaxy_group:
        galaxy_ids = {e["id"] for e in galaxy_group}
        disconnected = [e for e in disconnected if e["id"] not in galaxy_ids]

        existing_ids = {e["id"] for e in remaining}
        for g in galaxy_group:
            if g["id"] not in existing_ids:
                remaining.append(g)

    return disconnected, remaining


def group_has_github_urls(instances):
    """
    Return True if any repo/webpage URL in the group is a GitHub URL.
    Works for scheme-less URLs too.
    """
    for instance in instances:
        for repo in instance["data"].get("repository", []):
            url = repo.get("url")
            if url and is_github_url(url):
                return True

        for url in instance["data"].get("webpage", []):
            if url and is_github_url(url):
                return True

    return False


def find_disconnected_entries(data, use_name_match_for_no_links=True):
    """
    Two-stage conflict detection:

    1. Cheap normalization only
    2. Only if a block still has disconnected entries and contains GitHub URLs,
       retry that block with GitHub redirect resolution
    """
    disconnected_keys = {}

    for key, value in data.items():
        instances = value.get("instances", [])
        if not instances:
            continue

        # First pass: cheap only
        instance_details, instance_links = build_instance_representation(
            instances,
            resolve_github=False
        )

        if len(instance_details) <= 1:
            continue

        if all_entries_same_name_and_galaxy_related(instance_details):
            logging.debug(f"Skipping conflict for {key} — all Galaxy-related entries with same name.")
            continue

        disconnected, remaining = classify_entries(
            instance_details,
            instance_links,
            use_name_match_for_no_links=use_name_match_for_no_links
        )

        # Second pass: only if needed
        if disconnected and group_has_github_urls(instances):
            logging.debug(f"Retrying block {key} with GitHub resolution")

            instance_details_resolved, instance_links_resolved = build_instance_representation(
                instances,
                resolve_github=True
            )

            disconnected_resolved, remaining_resolved = classify_entries(
                instance_details_resolved,
                instance_links_resolved,
                use_name_match_for_no_links=use_name_match_for_no_links
            )

            disconnected = disconnected_resolved
            remaining = remaining_resolved

        if disconnected:
            disconnected_keys[key] = {
                "disconnected": disconnected,
                "remaining": remaining
            }

    resolved_conflicts = resolve_source_name_clusters(disconnected_keys)
    return resolved_conflicts


def token_size(text):
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

if __name__ == '__main__': 
    print(is_github_url("github.com/bcgsc/AMPd-Up"))
    print(normalize_url("github.com/bcgsc/AMPd-Up"))
    print(resolve_github_url("github.com/bcgsc/AMPd-Up"))
    print(get_normalized_link_variants("github.com/bcgsc/AMPd-Up", resolve_github=True))
    print(get_normalized_link_variants("github.com/BirolLab/AMPd-Up", resolve_github=True))
