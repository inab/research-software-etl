#!/usr/bin/env python3

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


BIOTOOLS_JSON = Path("scripts/proteomics/biotools_proteomics_tools.json")
BIOTOOLS_ONLY_JSON = Path("scripts/proteomics/comparison_output/biotools_only.json")
OUTPUT_DIR = Path("scripts/proteomics/comparison_output/confidence_flag_analysis")


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(obj, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def summarize_confidence_flags(tools: list[dict]) -> dict:
    counter = Counter()

    for tool in tools:
        value = tool.get("confidence_flag")
        if value is None:
            key = "null"
        else:
            key = str(value)
        counter[key] += 1

    total = len(tools)

    counts = dict(sorted(counter.items(), key=lambda x: x[0]))
    percentages = {
        key: round((count / total) * 100, 2) if total else 0.0
        for key, count in counts.items()
    }

    return {
        "total": total,
        "counts": counts,
        "percentages": percentages,
    }


def build_biotools_index(full_tools: list[dict]) -> dict[str, dict]:
    """
    Index full bio.tools tools by biotoolsID.
    """
    index = {}

    for tool in full_tools:
        biotools_id = tool.get("biotoolsID")
        if biotools_id:
            index[biotools_id] = tool

    return index


def recover_biotools_only_full_tools(
    biotools_only_entries: list[dict],
    full_tools: list[dict],
) -> tuple[list[dict], list[dict]]:
    """
    Recover the full tool objects corresponding to entries in biotools_only.json.

    Matching strategy:
    1. biotoolsID
    2. fallback to primary_name == name
    """
    by_biotools_id = build_biotools_index(full_tools)

    # fallback index by name
    by_name = {}
    for tool in full_tools:
        name = tool.get("name")
        if name:
            by_name[name] = tool

    recovered = []
    not_found = []

    for entry in biotools_only_entries:
        matched = None

        biotools_id = entry.get("biotoolsID")
        primary_name = entry.get("primary_name")

        if biotools_id and biotools_id in by_biotools_id:
            matched = by_biotools_id[biotools_id]
        elif primary_name and primary_name in by_name:
            matched = by_name[primary_name]

        if matched is not None:
            recovered.append(matched)
        else:
            not_found.append(entry)

    return recovered, not_found


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    full_tools = load_json(BIOTOOLS_JSON)
    biotools_only_entries = load_json(BIOTOOLS_ONLY_JSON)

    biotools_only_full, not_found = recover_biotools_only_full_tools(
        biotools_only_entries,
        full_tools,
    )

    biotools_only_ids = {
        tool.get("biotoolsID")
        for tool in biotools_only_full
        if tool.get("biotoolsID")
    }

    remaining_tools = [
        tool
        for tool in full_tools
        if tool.get("biotoolsID") not in biotools_only_ids
    ]

    biotools_only_summary = summarize_confidence_flags(biotools_only_full)
    remaining_summary = summarize_confidence_flags(remaining_tools)

    combined_summary = {
        "biotools_only": biotools_only_summary,
        "remaining_tools": remaining_summary,
        "not_found_count": len(not_found),
    }

    print(json.dumps(combined_summary, indent=2, ensure_ascii=False))

    save_json(biotools_only_full, OUTPUT_DIR / "biotools_only_full_tools.json")
    save_json(not_found, OUTPUT_DIR / "biotools_only_not_found.json")
    save_json(biotools_only_summary, OUTPUT_DIR / "biotools_only_confidence_summary.json")
    save_json(remaining_summary, OUTPUT_DIR / "remaining_tools_confidence_summary.json")
    save_json(combined_summary, OUTPUT_DIR / "confidence_summary_comparison.json")


if __name__ == "__main__":
    main()