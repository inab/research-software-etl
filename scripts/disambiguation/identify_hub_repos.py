#!/usr/bin/env python3
"""
Identify hub-like repositories from a grouping JSONL file using records fetched
directly from the pretools Mongo collection.

A hub-like repo is a repository that appears inside a grouped block and links
multiple clearly different tool names, causing false merges.

Typical use:
    python -m scripts.disambiguation.identify_hub_repos \
        --grouping-file data/integration/runs/<run_id>/grouped_entries.simplified.<run_id>.jsonl

Outputs:
- hub_repo_report.json
- hub_repo_blacklist.txt
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from urllib.parse import urlparse

from dotenv import load_dotenv

from infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


PRETOOLS_COLLECTION = "pretoolsDev"


def get_collection():
    return mongo_adapter.get_collection(PRETOOLS_COLLECTION)


# -----------------------------------------------------------------------------
# Loading grouping file
# -----------------------------------------------------------------------------

def load_grouping_jsonl(path: str) -> dict[str, dict]:
    """
    Load grouping JSONL as:
        {
            "group_key": {"instances": [...]},
            ...
        }
    """
    groups = {}

    with open(path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in grouping file at line {line_number}: {exc}"
                ) from exc

            if not isinstance(obj, dict) or len(obj) != 1:
                raise ValueError(
                    f"Expected one top-level group per line in grouping file "
                    f"(line {line_number}). Got: {obj}"
                )

            group_id, payload = next(iter(obj.items()))
            groups[group_id] = payload

    return groups


# -----------------------------------------------------------------------------
# Mongo fetch
# -----------------------------------------------------------------------------

def collect_instance_ids(groups: dict[str, dict]) -> list[str]:
    """
    Collect all unique instance _id values appearing in the grouping file.
    """
    ids = set()

    for payload in groups.values():
        for instance_id in payload.get("instances", []):
            if isinstance(instance_id, str) and instance_id.strip():
                ids.add(instance_id)

    return sorted(ids)


def load_pretools_records_by_id(instance_ids: list[str], batch_size: int = 1000) -> dict[str, dict]:
    """
    Fetch records from Mongo in batches and return a dict keyed by _id.
    """
    collection = get_collection()
    records_by_id = {}

    for i in range(0, len(instance_ids), batch_size):
        batch_ids = instance_ids[i:i + batch_size]

        cursor = collection.find({"_id": {"$in": batch_ids}})
        for record in cursor:
            record_id = record.get("_id")
            if record_id:
                records_by_id[record_id] = record

    return records_by_id


# -----------------------------------------------------------------------------
# Normalization
# -----------------------------------------------------------------------------

def normalize_tool_name(name: str | None) -> str | None:
    """
    Light normalization for names:
    - lowercase
    - remove separators such as _, -, spaces, dots

    Enough to merge obvious variants, but still keep different tools separate.
    """
    if not name or not isinstance(name, str):
        return None

    name = name.strip().lower()
    if not name:
        return None

    name = re.sub(r"[_\-\s\.]+", "", name)
    return name or None


def normalize_url(url: str | None) -> str | None:
    """
    Normalize URL for repo comparison:
    - lowercase domain
    - remove protocol
    - remove trailing slash
    - remove final .git
    - lowercase entire normalized string for robust matching
    """
    if not url or not isinstance(url, str):
        return None

    url = url.strip()
    if not url:
        return None

    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")

    if path.endswith(".git"):
        path = path[:-4]

    normalized = f"{netloc}{path}".lower().strip("/")
    return normalized or None


def looks_like_hub_repo(repo: str) -> bool:
    """
    Weak pattern hint only. Used as extra signal for review.
    """
    if not repo:
        return False

    patterns = [
        r"/tools[-_]",
        r"/wrappers?",
        r"/tool[-_]?wrappers?",
        r"/tool[-_]?collection",
        r"/suite",
        r"/galaxy",
        r"/galaxy[-_]",
    ]

    return any(re.search(pattern, repo) for pattern in patterns)


def as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


# -----------------------------------------------------------------------------
# Metadata extraction
# -----------------------------------------------------------------------------

def extract_candidate_names(record: dict) -> set[str]:
    """
    Extract possible tool names from record fields.
    Fallback to the second segment of _id: source/name/type/version
    """
    names = set()

    data = record.get("data", {})
    if not isinstance(data, dict):
        data = {}

    for value in [
        data.get("name"),
        record.get("name"),
    ]:
        norm = normalize_tool_name(value)
        if norm:
            names.add(norm)

    record_id = record.get("_id")
    if isinstance(record_id, str):
        parts = record_id.split("/")
        if len(parts) >= 2:
            norm = normalize_tool_name(parts[1])
            if norm:
                names.add(norm)

    return names


def extract_candidate_urls(record: dict) -> set[str]:
    """
    Extract possible repository-like URLs from common fields.

    This is intentionally broad. Later you can narrow it if you want to use only
    true repository fields.
    """
    urls = set()

    data = record.get("data", {})
    if not isinstance(data, dict):
        data = {}

    candidate_fields = [
        data.get("repository"),
        data.get("repo"),
        data.get("repository_url"),
        data.get("codeRepository"),
        data.get("download"),
        data.get("homepage"),
        data.get("webpage"),
        record.get("repository"),
        record.get("repo"),
        record.get("repository_url"),
        record.get("webpage"),
    ]

    for value in candidate_fields:
        for item in as_list(value):
            if isinstance(item, str):
                norm = normalize_url(item)
                if norm:
                    urls.add(norm)
            elif isinstance(item, dict):
                for key in ("url", "link", "value"):
                    maybe_url = item.get(key)
                    if isinstance(maybe_url, str):
                        norm = normalize_url(maybe_url)
                        if norm:
                            urls.add(norm)

    for field_name in ("web", "links", "repositories", "documentation"):
        for item in as_list(data.get(field_name)):
            if isinstance(item, str):
                norm = normalize_url(item)
                if norm:
                    urls.add(norm)
            elif isinstance(item, dict):
                for key in ("url", "link", "value"):
                    maybe_url = item.get(key)
                    if isinstance(maybe_url, str):
                        norm = normalize_url(maybe_url)
                        if norm:
                            urls.add(norm)

    return urls


# -----------------------------------------------------------------------------
# Analysis
# -----------------------------------------------------------------------------

def analyze_groups(
    groups: dict[str, dict],
    records_by_id: dict[str, dict],
    min_distinct_names: int = 3,
    min_records_per_repo_in_group: int = 3,
) -> tuple[list[dict], dict[str, dict]]:
    """
    Return:
    - suspicious group-level findings
    - aggregated repo-level summary
    """
    suspicious_groups = []
    repo_summary = defaultdict(lambda: {
        "groups": set(),
        "instance_ids": set(),
        "names": set(),
        "pattern_hint": False,
        "group_examples": [],
    })

    for group_id, payload in groups.items():
        instance_ids = payload.get("instances", [])
        if not instance_ids:
            continue

        repo_to_instances = defaultdict(list)
        repo_to_names = defaultdict(set)
        missing_records = []

        for instance_id in instance_ids:
            record = records_by_id.get(instance_id)
            if not record:
                missing_records.append(instance_id)
                continue

            names = extract_candidate_names(record)
            repos = extract_candidate_urls(record)

            for repo in repos:
                repo_to_instances[repo].append(instance_id)
                repo_to_names[repo].update(names)

        for repo, repo_instances in repo_to_instances.items():
            distinct_names = repo_to_names[repo]

            if (
                len(repo_instances) >= min_records_per_repo_in_group
                and len(distinct_names) >= min_distinct_names
            ):
                suspicious_groups.append({
                    "group_id": group_id,
                    "repo": repo,
                    "repo_instance_count_in_group": len(repo_instances),
                    "distinct_names_in_group": sorted(distinct_names),
                    "instance_ids_for_repo_in_group": sorted(repo_instances),
                    "hub_pattern_hint": looks_like_hub_repo(repo),
                    "missing_records_in_group": sorted(missing_records),
                })

                repo_summary[repo]["groups"].add(group_id)
                repo_summary[repo]["instance_ids"].update(repo_instances)
                repo_summary[repo]["names"].update(distinct_names)
                repo_summary[repo]["pattern_hint"] = (
                    repo_summary[repo]["pattern_hint"] or looks_like_hub_repo(repo)
                )
                repo_summary[repo]["group_examples"].append({
                    "group_id": group_id,
                    "names": sorted(distinct_names),
                    "repo_instance_count_in_group": len(repo_instances),
                })

    repo_summary_final = {}
    for repo, info in repo_summary.items():
        repo_summary_final[repo] = {
            "group_count": len(info["groups"]),
            "instance_count": len(info["instance_ids"]),
            "distinct_names": sorted(info["names"]),
            "distinct_name_count": len(info["names"]),
            "pattern_hint": info["pattern_hint"],
            "group_examples": sorted(
                info["group_examples"],
                key=lambda x: (x["repo_instance_count_in_group"], x["group_id"]),
                reverse=True,
            ),
        }

    return suspicious_groups, repo_summary_final


def rank_blacklist_candidates(repo_summary: dict[str, dict]) -> list[dict]:
    """
    Rank candidates so the strongest blacklist suspects appear first.
    """
    candidates = []

    for repo, info in repo_summary.items():
        score = (
            info["group_count"] * 5
            + info["distinct_name_count"] * 3
            + info["instance_count"]
            + (5 if info["pattern_hint"] else 0)
        )

        candidates.append({
            "repo": repo,
            "score": score,
            **info,
        })

    candidates.sort(
        key=lambda x: (
            x["score"],
            x["distinct_name_count"],
            x["group_count"],
            x["instance_count"],
        ),
        reverse=True,
    )

    return candidates


# -----------------------------------------------------------------------------
# Output
# -----------------------------------------------------------------------------

def write_json(path: str, payload) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def write_blacklist_txt(path: str, candidates: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for candidate in candidates:
            f.write(candidate["repo"] + "\n")


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Identify hub-like repositories from a grouping JSONL file."
    )
    parser.add_argument(
        "--grouping-file",
        required=True,
        help="Path to grouping JSONL file.",
    )
    parser.add_argument(
        "--collection",
        default=PRETOOLS_COLLECTION,
        help="Mongo collection name for pretools records.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Environment file to initialize Mongo connection.",
    )
    parser.add_argument(
        "--min-distinct-names",
        type=int,
        default=3,
        help="Minimum number of distinct names linked to the same repo in one group.",
    )
    parser.add_argument(
        "--min-records-per-repo-in-group",
        type=int,
        default=3,
        help="Minimum number of records in the same group sharing a repo.",
    )
    parser.add_argument(
        "--report-json",
        default="scripts/disambiguation/hub_repo_report.json",
        help="Output JSON report path.",
    )
    parser.add_argument(
        "--blacklist-output",
        default="scripts/disambiguation/hub_repo_blacklist.txt",
        help="Output text file with one candidate repo per line.",
    )

    args = parser.parse_args()

    load_dotenv(args.env_file)

    groups = load_grouping_jsonl(args.grouping_file)
    instance_ids = collect_instance_ids(groups)
    records_by_id = load_pretools_records_by_id(instance_ids)

    suspicious_groups, repo_summary = analyze_groups(
        groups=groups,
        records_by_id=records_by_id,
        min_distinct_names=args.min_distinct_names,
        min_records_per_repo_in_group=args.min_records_per_repo_in_group,
    )

    blacklist_candidates = rank_blacklist_candidates(repo_summary)

    report = {
        "summary": {
            "group_count": len(groups),
            "instance_id_count_in_grouping": len(instance_ids),
            "records_fetched_from_mongo": len(records_by_id),
            "missing_records": len(instance_ids) - len(records_by_id),
            "suspicious_group_findings": len(suspicious_groups),
            "blacklist_candidate_count": len(blacklist_candidates),
        },
        "suspicious_groups": suspicious_groups,
        "blacklist_candidates": blacklist_candidates,
    }

    write_json(args.report_json, report)
    write_blacklist_txt(args.blacklist_output, blacklist_candidates)

    print(f"Saved report to: {args.report_json}")
    print(f"Saved blacklist candidates to: {args.blacklist_output}")
    print(f"Grouping blocks analyzed: {len(groups)}")
    print(f"Instance ids referenced: {len(instance_ids)}")
    print(f"Mongo records fetched: {len(records_by_id)}")
    print(f"Suspicious findings: {len(suspicious_groups)}")
    print(f"Candidate repos: {len(blacklist_candidates)}")


if __name__ == "__main__":
    main()