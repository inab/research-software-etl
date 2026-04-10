import logging
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


def are_same_by_source_and_name(entry1, entry2):
    name1 = entry1.get("name", "").strip().lower()
    name2 = entry2.get("name", "").strip().lower()
    sources1 = set(map(str.lower, entry1.get("source", [])))
    sources2 = set(map(str.lower, entry2.get("source", [])))
    return name1 == name2 and bool(sources1 & sources2)


def apply_source_name_merge(conflict_blocks):
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
    return all(is_galaxy_related(entry) for entry in instance_details)


def get_galaxy_related_same_name(entries):
    name_counter = {}
    for e in entries:
        if is_galaxy_related(e):
            name = e["name"].strip().lower()
            name_counter[name] = name_counter.get(name, 0) + 1

    if not name_counter:
        return []

    common_name = max(name_counter.items(), key=lambda x: x[1])[0]
    return [
        e for e in entries
        if is_galaxy_related(e) and e["name"].strip().lower() == common_name
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

    return disconnected_keys


def token_size(text):
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))

if __name__ == '__main__': 
    print(is_github_url("github.com/bcgsc/AMPd-Up"))
    print(normalize_url("github.com/bcgsc/AMPd-Up"))
    print(resolve_github_url("github.com/bcgsc/AMPd-Up"))
    print(get_normalized_link_variants("github.com/bcgsc/AMPd-Up", resolve_github=True))
    print(get_normalized_link_variants("github.com/BirolLab/AMPd-Up", resolve_github=True))
