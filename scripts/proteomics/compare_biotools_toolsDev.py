#!/usr/bin/env python3

"""
Compare Proteomics tools from:
- bio.tools dump stored in scripts/proteomics
- MongoDB toolsDev collection, filtered by data.tags containing "Proteomics"

It compares Mongo names against these candidate names from bio.tools:
- name
- biotoolsID

And compares them to:
- data.name
- each value in data.label

It generates:
- exact match report
- normalized match report
- mongo-only tools
- biotools-only tools
- fuzzy suggestions for mongo-only tools
- docs with more than one aggregated biotools/<biotoolsID> source
- docs with more than one aggregated biotools/<biotoolsID> source
  that belongs to scripts/proteomics/biotools_proteomics_tools.json
"""

from __future__ import annotations

import json
import re
import unicodedata
from difflib import get_close_matches
from pathlib import Path

from infrastructure.db.mongo.mongo_adapter import MongoDBAdapter

mongo_adapter = MongoDBAdapter()


BIOTOOLS_JSON = Path("scripts/proteomics/biotools_proteomics_tools.json")
OUTPUT_DIR = Path("scripts/proteomics/comparison_output")
TOOLS_COLLECTION = "toolsDev"
TARGET_TAG = "Proteomics"


def normalize_string_list(value) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        value = [value]

    if not isinstance(value, list):
        return []

    out = []
    for item in value:
        if isinstance(item, str):
            item = item.strip()
            if item:
                out.append(item)
    return out


def normalize_name(text: str) -> str:
    if not text:
        return ""

    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("&", " and ")
    text = re.sub(r"[-_/]", " ", text)
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def load_biotools_tools(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def extract_biotools_names(biotools_tools: list[dict]) -> list[dict]:
    """
    Each bio.tools entry contributes multiple candidate names:
    - name
    - biotoolsID

    Output format:
    [
      {
        "primary_name": "...",
        "biotoolsID": "...",
        "candidate_names": [...],
        "candidate_norm_names": [...],
      }
    ]
    """
    out = []

    for tool in biotools_tools:
        primary_name = (tool.get("name") or "").strip()
        biotools_id = (tool.get("biotoolsID") or "").strip()
        biotools_curie = (tool.get("biotoolsCURIE") or "").strip()

        candidate_names = []
        for value in [primary_name, biotools_id]:
            if value and value not in candidate_names:
                candidate_names.append(value)

        if not candidate_names:
            continue

        out.append(
            {
                "primary_name": primary_name,
                "biotoolsID": biotools_id,
                "biotoolsCURIE": biotools_curie,
                "candidate_names": candidate_names,
                "candidate_norm_names": [normalize_name(x) for x in candidate_names],
            }
        )

    return out


def load_mongo_proteomics_tools() -> list[dict]:
    collection = mongo_adapter.get_collection(TOOLS_COLLECTION)

    query = {"data.tags": {"$in": ["Proteomics", "proteomics"]}}
    projection = {
        "_id": 1,
        "id": 1,
        "source": 1,  # top-level aggregated source ids
        "data.name": 1,
        "data.label": 1,
        "data.tags": 1,
    }

    return list(collection.find(query, projection))


def extract_distinct_biotools_prefixes(sources: list[str]) -> list[str]:
    """
    From aggregated source ids like:
        biotools/<biotoolsID>/<type>/<version>
    extract distinct prefixes:
        biotools/<biotoolsID>

    Returns them sorted for stable output.
    """
    prefixes = set()

    for src in sources:
        if not isinstance(src, str):
            continue

        parts = src.strip().split("/")
        if len(parts) < 2:
            continue

        if parts[0].lower() != "biotools":
            continue

        prefix = f"biotools/{parts[1].lower()}"
        prefixes.add(prefix)

    return sorted(prefixes)


def build_allowed_biotools_prefixes(biotools_tools: list[dict]) -> set[str]:
    """
    Build:
        {"biotools/<biotoolsID>", ...}
    from the proteomics JSON file.
    """
    allowed = set()

    for tool in biotools_tools:
        biotools_id = (tool.get("biotoolsID") or "").strip().lower()
        if biotools_id:
            allowed.add(f"biotools/{biotools_id}")

    return allowed


def extract_mongo_names(mongo_tools: list[dict]) -> list[dict]:
    out = []

    for tool in mongo_tools:
        data = tool.get("data", {}) or {}

        name = (data.get("name") or "").strip()
        labels = normalize_string_list(data.get("label"))
        sources = normalize_string_list(tool.get("source"))
        biotools_sources = extract_distinct_biotools_prefixes(sources)

        out.append(
            {
                "_id": str(tool.get("_id")),
                "id": tool.get("id"),
                "name": name,
                "labels": labels,
                "norm_name": normalize_name(name),
                "norm_labels": [normalize_name(label) for label in labels],
                "sources": sources,
                "biotools_sources": biotools_sources,
                "biotools_source_count": len(biotools_sources),
                "tags": normalize_string_list(data.get("tags")),
            }
        )

    return out


def build_name_index_biotools(
    biotools_entries: list[dict],
) -> tuple[set[str], set[str], dict[str, list[dict]]]:
    """
    Builds indexes over all bio.tools candidate names:
    - exact candidate names
    - normalized candidate names
    - normalized candidate name -> matching bio.tools entries
    """
    exact_names = set()
    norm_names = set()
    by_norm = {}

    for entry in biotools_entries:
        for candidate_name, candidate_norm_name in zip(
            entry["candidate_names"], entry["candidate_norm_names"]
        ):
            exact_names.add(candidate_name)
            norm_names.add(candidate_norm_name)
            by_norm.setdefault(candidate_norm_name, []).append(
                {
                    "primary_name": entry["primary_name"],
                    "biotoolsID": entry["biotoolsID"],
                    "biotoolsCURIE": entry["biotoolsCURIE"],
                    "matched_candidate_name": candidate_name,
                    "matched_candidate_norm_name": candidate_norm_name,
                }
            )

    return exact_names, norm_names, by_norm


def compare(mongo_entries: list[dict], biotools_entries: list[dict]) -> dict:
    biotools_exact_names, biotools_norm_names, biotools_by_norm = build_name_index_biotools(
        biotools_entries
    )

    matched_exact = []
    matched_normalized = []
    mongo_only = []

    matched_biotools_norms = set()

    for tool in mongo_entries:
        name = tool["name"]
        labels = tool["labels"]
        norm_name = tool["norm_name"]
        norm_labels = tool["norm_labels"]

        norm_hit = None
        exact_hits = []

        if name in biotools_exact_names:
            exact_hits.append(("name", name))

        for label in labels:
            if label in biotools_exact_names:
                exact_hits.append(("label", label))

        if exact_hits:
            biotools_candidates = []
            seen_norms = set()

            for hit_type, hit_value in exact_hits:
                norm_value = normalize_name(hit_value)
                seen_norms.add(norm_value)
                biotools_candidates.extend(biotools_by_norm.get(norm_value, []))

            matched_exact.append(
                {
                    **tool,
                    "matched_on": exact_hits,
                    "matched_values": [v for _, v in exact_hits],
                    "biotools_candidates": biotools_candidates,
                }
            )

            matched_biotools_norms.update(seen_norms)
            continue

        if norm_name and norm_name in biotools_norm_names:
            norm_hit = ("name", name)
        else:
            for norm_label, raw_label in zip(norm_labels, labels):
                if norm_label and norm_label in biotools_norm_names:
                    norm_hit = ("label", raw_label)
                    break

        if norm_hit:
            norm_value = normalize_name(norm_hit[1])
            candidates = biotools_by_norm.get(norm_value, [])
            matched_normalized.append(
                {
                    **tool,
                    "matched_on": norm_hit[0],
                    "matched_value": norm_hit[1],
                    "matched_normalized_value": norm_value,
                    "biotools_candidates": candidates,
                }
            )
            matched_biotools_norms.add(norm_value)
        else:
            mongo_only.append(tool)

    biotools_only = []
    for entry in biotools_entries:
        entry_norms = set(entry["candidate_norm_names"])
        if not entry_norms.intersection(matched_biotools_norms):
            biotools_only.append(entry)

    return {
        "matched_exact": matched_exact,
        "matched_normalized": matched_normalized,
        "mongo_only": mongo_only,
        "biotools_only": biotools_only,
    }


def find_multi_biotools_aggregations(mongo_entries: list[dict]) -> list[dict]:
    """
    Return Mongo docs that aggregate more than one distinct biotools/<biotoolsID>.
    """
    return [
        tool
        for tool in mongo_entries
        if tool.get("biotools_source_count", 0) > 1
    ]


def find_multi_proteomics_biotools_aggregations(
    mongo_entries: list[dict],
    allowed_biotools_prefixes: set[str],
) -> list[dict]:
    """
    Return Mongo docs that aggregate more than one distinct biotools/<biotoolsID>
    AND where those biotools ids are in scripts/proteomics/biotools_proteomics_tools.json.
    """
    results = []

    for tool in mongo_entries:
        matching_proteomics_sources = [
            src
            for src in tool.get("biotools_sources", [])
            if src in allowed_biotools_prefixes
        ]

        if len(matching_proteomics_sources) > 1:
            results.append(
                {
                    **tool,
                    "proteomics_biotools_sources": matching_proteomics_sources,
                    "proteomics_biotools_source_count": len(matching_proteomics_sources),
                }
            )

    return results


def add_fuzzy_suggestions(
    mongo_only: list[dict], biotools_entries: list[dict], n: int = 5
) -> list[dict]:
    """
    Fuzzy-match mongo-only names against all bio.tools candidate names.
    """
    biotools_name_lookup = {}
    for entry in biotools_entries:
        for candidate_name, candidate_norm_name in zip(
            entry["candidate_names"], entry["candidate_norm_names"]
        ):
            biotools_name_lookup[candidate_norm_name] = {
                "primary_name": entry["primary_name"],
                "biotoolsID": entry["biotoolsID"],
                "biotoolsCURIE": entry["biotoolsCURIE"],
                "matched_candidate_name": candidate_name,
            }

    biotools_norm_names = list(biotools_name_lookup.keys())

    results = []
    for tool in mongo_only:
        query_values = []

        if tool["norm_name"]:
            query_values.append(tool["norm_name"])

        for norm_label in tool["norm_labels"]:
            if norm_label and norm_label not in query_values:
                query_values.append(norm_label)

        suggested = []
        seen = set()

        for q in query_values:
            for match in get_close_matches(q, biotools_norm_names, n=n, cutoff=0.75):
                if match not in seen:
                    seen.add(match)
                    suggestion = biotools_name_lookup[match]
                    suggested.append(
                        {
                            "normalized_match": match,
                            "primary_name": suggestion["primary_name"],
                            "biotoolsID": suggestion["biotoolsID"],
                            "biotoolsCURIE": suggestion["biotoolsCURIE"],
                            "matched_candidate_name": suggestion["matched_candidate_name"],
                        }
                    )

        results.append(
            {
                **tool,
                "fuzzy_suggestions": suggested,
            }
        )

    return results


def save_json(obj, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def save_jsonl(rows: list[dict], path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    biotools_tools = load_biotools_tools(BIOTOOLS_JSON)
    biotools_entries = extract_biotools_names(biotools_tools)
    allowed_biotools_prefixes = build_allowed_biotools_prefixes(biotools_tools)

    mongo_tools = load_mongo_proteomics_tools()
    mongo_entries = extract_mongo_names(mongo_tools)

    multi_biotools_aggregations = find_multi_biotools_aggregations(mongo_entries)
    multi_proteomics_biotools_aggregations = find_multi_proteomics_biotools_aggregations(
        mongo_entries,
        allowed_biotools_prefixes,
    )

    print("---- checking wiff2dta on bio.tools side ----")
    print(
        "wiff2dta in exact names?",
        "wiff2dta" in build_name_index_biotools(biotools_entries)[0],
    )

    for entry in biotools_entries:
        if "wiff2dta" in entry["candidate_names"] or "wiff2dta" in entry["candidate_norm_names"]:
            print("BIO MATCH CANDIDATE:", json.dumps(entry, indent=2, ensure_ascii=False))

    print("---- checking wiff2dta on mongo side ----")
    for tool in mongo_entries:
        if tool["name"] == "quant" or "wiff2dta" in tool["labels"] or "wiff2dta" in tool["norm_labels"]:
            print("MONGO CANDIDATE:", json.dumps(tool, indent=2, ensure_ascii=False))

    comparison = compare(mongo_entries, biotools_entries)
    mongo_only_with_suggestions = add_fuzzy_suggestions(
        comparison["mongo_only"], biotools_entries
    )

    print("\n---- sanity check for wiff2dta after compare() ----")

    matched_rows = []

    for row in comparison["matched_exact"]:
        multi_values = row.get("matched_values", [])

        if "wiff2dta" in multi_values:
            matched_rows.append(row)
            continue

        if any(c.get("biotoolsID") == "wiff2dta" for c in row.get("biotools_candidates", [])):
            matched_rows.append(row)

    for row in comparison["matched_normalized"]:
        if row.get("matched_value") == "wiff2dta":
            matched_rows.append(row)
            continue

        if any(c.get("biotoolsID") == "wiff2dta" for c in row.get("biotools_candidates", [])):
            matched_rows.append(row)

    biotools_only_rows = [
        row for row in comparison["biotools_only"]
        if row["biotoolsID"] == "wiff2dta"
        or row["primary_name"] == "wiff2dta"
    ]

    print("matched rows:", len(matched_rows))
    for row in matched_rows:
        print(json.dumps(row, indent=2, ensure_ascii=False))

    print("biotools_only rows:", len(biotools_only_rows))
    for row in biotools_only_rows:
        print(json.dumps(row, indent=2, ensure_ascii=False))

    print("\n---- docs with multiple aggregated bio.tools tools ----")
    print("count:", len(multi_biotools_aggregations))
    for row in multi_biotools_aggregations[:20]:
        print(
            json.dumps(
                {
                    "_id": row["_id"],
                    "id": row["id"],
                    "name": row["name"],
                    "labels": row["labels"],
                    "sources": row["sources"],
                    "biotools_sources": row["biotools_sources"],
                    "biotools_source_count": row["biotools_source_count"],
                },
                indent=2,
                ensure_ascii=False,
            )
        )

    print("\n---- docs with multiple aggregated proteomics bio.tools tools ----")
    print("count:", len(multi_proteomics_biotools_aggregations))
    for row in multi_proteomics_biotools_aggregations[:20]:
        print(
            json.dumps(
                {
                    "_id": row["_id"],
                    "id": row["id"],
                    "name": row["name"],
                    "labels": row["labels"],
                    "sources": row["sources"],
                    "proteomics_biotools_sources": row["proteomics_biotools_sources"],
                    "proteomics_biotools_source_count": row["proteomics_biotools_source_count"],
                },
                indent=2,
                ensure_ascii=False,
            )
        )

    summary = {
        "biotools_count": len(biotools_entries),
        "mongo_count": len(mongo_entries),
        "matched_exact": len(comparison["matched_exact"]),
        "matched_normalized": len(comparison["matched_normalized"]),
        "mongo_only": len(comparison["mongo_only"]),
        "biotools_only": len(comparison["biotools_only"]),
        "multi_biotools_aggregations": len(multi_biotools_aggregations),
        "multi_proteomics_biotools_aggregations": len(multi_proteomics_biotools_aggregations),
    }

    print(json.dumps(summary, indent=2, ensure_ascii=False))

    save_json(summary, OUTPUT_DIR / "summary.json")
    save_json(comparison["matched_exact"], OUTPUT_DIR / "matched_exact.json")
    save_json(comparison["matched_normalized"], OUTPUT_DIR / "matched_normalized.json")
    save_json(comparison["mongo_only"], OUTPUT_DIR / "mongo_only.json")
    save_json(comparison["biotools_only"], OUTPUT_DIR / "biotools_only.json")
    save_json(
        mongo_only_with_suggestions,
        OUTPUT_DIR / "mongo_only_with_fuzzy_suggestions.json",
    )
    save_json(
        multi_biotools_aggregations,
        OUTPUT_DIR / "multi_biotools_aggregations.json",
    )
    save_json(
        multi_proteomics_biotools_aggregations,
        OUTPUT_DIR / "multi_proteomics_biotools_aggregations.json",
    )

    save_jsonl(comparison["matched_exact"], OUTPUT_DIR / "matched_exact.jsonl")
    save_jsonl(comparison["matched_normalized"], OUTPUT_DIR / "matched_normalized.jsonl")
    save_jsonl(
        mongo_only_with_suggestions,
        OUTPUT_DIR / "mongo_only_with_fuzzy_suggestions.jsonl",
    )
    save_jsonl(comparison["biotools_only"], OUTPUT_DIR / "biotools_only.jsonl")
    save_jsonl(
        multi_biotools_aggregations,
        OUTPUT_DIR / "multi_biotools_aggregations.jsonl",
    )
    save_jsonl(
        multi_proteomics_biotools_aggregations,
        OUTPUT_DIR / "multi_proteomics_biotools_aggregations.jsonl",
    )

    print(f"\nReports written to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()