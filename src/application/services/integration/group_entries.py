from collections import defaultdict
from urllib.parse import urlparse
import logging


# -----------------------------------------------------------------------------
# URL NORMALIZATION
# -----------------------------------------------------------------------------

def normalize_url(url: str) -> str | None:
    """
    Normalize a URL so equivalent repository/webpage links can be matched.

    Current normalization rules:
    - remove protocol
    - lowercase domain
    - remove trailing slash
    - special handling for Bioconductor package pages
    - remove final '.html' when present in Bioconductor-like pages

    Examples:
    - https://github.com/user/repo/        -> github.com/user/repo
    - http://bioconductor.org/packages/release/bioc/html/edgeR.html
      -> bioconductor.org/packages/edgeR
    """
    if not url or not isinstance(url, str):
        return None

    parsed_url = urlparse(url.strip())
    netloc = parsed_url.netloc.lower().strip()
    path = parsed_url.path.strip().rstrip("/")

    if not netloc:
        return None

    # Remove final ".html" from Bioconductor pages or similar package pages
    if path.endswith(".html"):
        path = path[:-5]

    # Special handling for Bioconductor package URLs
    if "bioconductor.org" in netloc:
        parts = [p for p in path.split("/") if p]
        for part in reversed(parts):
            if part not in ("release", "bioc", "html", "packages"):
                return f"bioconductor.org/packages/{part}"

    return f"{netloc}{path}".lower()


# -----------------------------------------------------------------------------
# NORMALIZATION HELPERS
# -----------------------------------------------------------------------------

def normalize_name(name: str) -> str:
    """
    Normalize software name for grouping by name.

    Current policy:
    - lowercase
    - strip leading/trailing spaces

    You may later decide to make this more aggressive
    (replace underscores/dashes/spaces, etc.), but for now it stays conservative.
    """
    if name is None:
        return ""
    return str(name).strip().lower()


def normalize_type(software_type) -> str:
    """
    Normalize type for grouping.

    Rules:
    - None -> "*"
    - empty string -> "*"
    - 'undefined' -> "*"
    - otherwise lowercase stripped string
    """
    if software_type is None:
        return "*"

    software_type = str(software_type).strip().lower()
    if not software_type or software_type == "undefined":
        return "*"

    return software_type


def safe_list(value):
    """
    Ensure value is always iterable as a list.

    Handles:
    - None -> []
    - list -> as is
    - scalar -> [scalar]
    """
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


# -----------------------------------------------------------------------------
# LINK EXTRACTION
# -----------------------------------------------------------------------------

def should_ignore_repository_url(url: str) -> bool:
    """
    Return True for repository URLs that should be ignored for grouping.

    These links are treated as if they did not exist.
    TODO: make a black list of URLs like this one
    """
    if not url or not isinstance(url, str):
        return False

    normalized = normalize_url(url)
    return normalized == "emboss.open-bio.org/html/adm/ch01s01"


def extract_grouping_links(inst: dict) -> set[str]:
    """
    Extract and normalize links that should contribute to grouping.

    We use:
    - repository URLs from data.repository
    - webpage URLs only if they look like repository/package-hosting pages

    This keeps generic homepages from causing accidental merges.
    """
    links = set()

    data = inst.get("data", {})

    # Repository links
    for repo in safe_list(data.get("repository")):
        if isinstance(repo, dict):
            url = repo.get("url")

            if should_ignore_repository_url(url):
                continue

            normalized_url = normalize_url(url)
            if normalized_url:
                links.add(normalized_url)

    # Webpages that should count as repository/package links
    repository_like_domains = [
        "github.com",
        "sourceforge.net",
        "gitlab.com",
        "bitbucket.org",
        "bioconductor.org/packages",
        "pypi.org/project",
        "metacpan.org/pod",
        "cran.r-project.org/package",
    ]

    for web_link in safe_list(data.get("webpage")):
        normalized_url = normalize_url(web_link)
        if normalized_url and any(domain in normalized_url for domain in repository_like_domains):
            links.add(normalized_url)

    return links


# -----------------------------------------------------------------------------
# UNION-FIND / DISJOINT SET
# -----------------------------------------------------------------------------

class UnionFind:
    """
    Simple Union-Find structure to keep track of merged groups.

    We use group keys (name/type identifiers) as nodes.
    """

    def __init__(self):
        self.parent = {}

    def add(self, x):
        if x not in self.parent:
            self.parent[x] = x

    def find(self, x):
        self.add(x)
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])  # path compression
        return self.parent[x]

    def union(self, a, b):
        """
        Merge the sets containing a and b.
        Returns the root after merging.
        """
        root_a = self.find(a)
        root_b = self.find(b)

        if root_a == root_b:
            return root_a

        # No ranking for now; can be added later if needed
        self.parent[root_b] = root_a
        return root_a


# -----------------------------------------------------------------------------
# MAIN GROUPING FUNCTION
# -----------------------------------------------------------------------------

def group_by_key_with_links(instances, logger: logging.Logger | None = None):
    """
    Group software entries using:
    1. normalized name + normalized type
    2. repository/package links
    3. real wildcard matching for name/*

    IMPORTANT IMPROVEMENTS OVER THE PREVIOUS VERSION
    ------------------------------------------------
    1. Wildcard '*' now behaves like a real wildcard during matching:
       - name/* can match name/cmd, name/workflow, etc.
       - name/cmd can match an existing name/*

    2. Final relabelling no longer overwrites groups silently:
       - if two groups produce the same final new_id, they are merged

    3. Uses Union-Find to keep merge relationships explicit and safer.

    Returns
    -------
    dict
        {
            "group_id": {
                "instances": [...],
                "links": [...]
            },
            ...
        }

    Notes
    -----
    Each instance is assumed to have:
    - inst["data"]["name"]
    - optional inst["data"]["type"]
    - optional inst["data"]["repository"]
    - optional inst["data"]["webpage"]
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # -------------------------------------------------------------------------
    # Internal indexes
    # -------------------------------------------------------------------------

    # Union-find to manage merges between provisional keys
    uf = UnionFind()

    # Map normalized link -> set of provisional keys seen with that link
    link_to_keys = defaultdict(set)

    # Map exact provisional key -> itself
    # Example key: "intarna/cmd"
    # Example wildcard key: "intarna/*"
    name_type_to_keys = defaultdict(set)

    # Store the actual data attached to each provisional key
    # We build this incrementally, then consolidate later through Union-Find.
    provisional_groups = {}

    # -------------------------------------------------------------------------
    # Step 1: create provisional groups and connect them by links / wildcard logic
    # -------------------------------------------------------------------------

    for idx, inst in enumerate(instances):
        data = inst.get("data", {})

        raw_name = data.get("name")
        if not raw_name:
            logger.warning("Skipping instance without data.name: %s", inst.get("_id"))
            continue

        name = normalize_name(raw_name)
        software_type = normalize_type(data.get("type"))
        exact_key = f"{name}/{software_type}"
        wildcard_key = f"{name}/*"

        links = extract_grouping_links(inst)

        # Initialize provisional group for this exact key if missing
        if exact_key not in provisional_groups:
            provisional_groups[exact_key] = {
                "instances": [],
                "links": set(),
            }

        provisional_groups[exact_key]["instances"].append(inst)
        provisional_groups[exact_key]["links"].update(links)

        uf.add(exact_key)

        # ---------------------------------------------------------------------
        # Find all keys this instance should connect to
        # ---------------------------------------------------------------------
        matching_keys = set()

        # 1. Same exact key
        matching_keys.update(name_type_to_keys.get(exact_key, set()))

        # 2. Real wildcard matching:
        #    - if this is name/cmd, also match name/*
        #    - if this is name/*, match all existing name/X
        matching_keys.update(name_type_to_keys.get(wildcard_key, set()))

        if software_type == "*":
            # Match all same-name keys regardless of type
            for existing_key in list(name_type_to_keys.keys()):
                existing_name, _, _ = existing_key.partition("/")
                if existing_name == name:
                    matching_keys.update(name_type_to_keys[existing_key])

        # 3. Shared repository/package links
        for link in links:
            matching_keys.update(link_to_keys.get(link, set()))

        # ---------------------------------------------------------------------
        # Union all matching keys with the current exact key
        # ---------------------------------------------------------------------
        for match in matching_keys:
            uf.union(exact_key, match)

        # ---------------------------------------------------------------------
        # Update indexes after unions
        # ---------------------------------------------------------------------
        name_type_to_keys[exact_key].add(exact_key)
        if software_type == "*":
            name_type_to_keys[wildcard_key].add(exact_key)

        for link in links:
            link_to_keys[link].add(exact_key)

    # -------------------------------------------------------------------------
    # Step 2: consolidate provisional groups by Union-Find root
    # -------------------------------------------------------------------------

    consolidated_groups = {}

    for provisional_key, payload in provisional_groups.items():
        root = uf.find(provisional_key)

        if root not in consolidated_groups:
            consolidated_groups[root] = {
                "instances": [],
                "links": set(),
            }

        consolidated_groups[root]["instances"].extend(payload["instances"])
        consolidated_groups[root]["links"].update(payload["links"])

    # -------------------------------------------------------------------------
    # Step 3: assign final group IDs safely
    # -------------------------------------------------------------------------
    #
    # Important:
    # The previous implementation could silently overwrite groups if two groups
    # generated the same final new_id.
    #
    # Here, if that happens, we MERGE instead of overwrite.
    # -------------------------------------------------------------------------

    final_groups = {}
    relabel_collisions = 0
    relabel_changed = 0

    for root_key, payload in consolidated_groups.items():
        group_instances = payload["instances"]

        names = []
        types = []

        for item in group_instances:
            item_data = item.get("data", {})
            names.append(normalize_name(item_data.get("name")))
            types.append(normalize_type(item_data.get("type")))

        unique_names = {n for n in names if n}
        unique_types = {t for t in types if t}

        # Decide final ID
        #
        # Policy:
        # - if there is more than one unique name, choose the shortest name
        # - if there is more than one unique type, use '*'
        # - otherwise preserve the single value
        #
        # This matches your previous logic, but now safely.
        if len(unique_names) > 1 or len(unique_types) > 1:
            name_id = min(unique_names, key=len) if unique_names else "unknown"
            type_id = "*" if len(unique_types) > 1 else (next(iter(unique_types)) if unique_types else "*")
            new_id = f"{name_id}/{type_id}"
            relabel_changed += 1
        else:
            # preserve original consolidated root key if it is already stable
            new_id = root_key

        # Safe merge instead of overwrite
        if new_id not in final_groups:
            final_groups[new_id] = {
                "instances": [],
                "links": set(),
            }
        else:
            relabel_collisions += 1
            logger.warning(
                "Final relabel collision for '%s'. Merging groups instead of overwriting.",
                new_id
            )

        final_groups[new_id]["instances"].extend(group_instances)
        final_groups[new_id]["links"].update(payload["links"])

    # -------------------------------------------------------------------------
    # Step 4: deduplicate instances inside each final group
    # -------------------------------------------------------------------------
    #
    # Because multiple provisional keys may have been merged, and because final
    # relabel collisions are now merged safely, deduplication is useful.
    # We deduplicate by instance _id.
    # -------------------------------------------------------------------------

    for group_id, payload in final_groups.items():
        seen_ids = set()
        deduped_instances = []

        for inst in payload["instances"]:
            inst_id = str(inst.get("_id"))
            if inst_id not in seen_ids:
                deduped_instances.append(inst)
                seen_ids.add(inst_id)

        payload["instances"] = deduped_instances
        payload["links"] = sorted(payload["links"])

    logger.info("Grouping completed.")
    logger.info("Provisional groups: %d", len(provisional_groups))
    logger.info("Consolidated groups: %d", len(consolidated_groups))
    logger.info("Final groups: %d", len(final_groups))
    logger.info("Groups relabelled: %d", relabel_changed)
    logger.info("Final relabel collisions merged safely: %d", relabel_collisions)

    print(f"Groups relabelled: {relabel_changed}")
    print(f"Final relabel collisions merged safely: {relabel_collisions}")

    return final_groups