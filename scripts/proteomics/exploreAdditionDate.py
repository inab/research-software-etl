#!/usr/bin/env python3

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from datetime import datetime, timezone



BIOTOOLS_JSON = Path("scripts/proteomics/biotools_proteomics_tools.json")
BIOTOOLS_ONLY_JSON = Path("scripts/proteomics/comparison_output/biotools_only.json")
OUTPUT_DIR = Path("scripts/proteomics/comparison_output/addition_date_analysis")


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(obj, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def build_biotools_index(full_tools: list[dict]) -> dict[str, dict]:
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
    by_biotools_id = build_biotools_index(full_tools)

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


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None

    value = value.strip()
    if not value:
        return None

    dt = None

    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(value, fmt)
            break
        except ValueError:
            pass

    if dt is None:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    # Normalize to naive UTC so all datetimes are comparable
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)

    return dt


def extract_addition_date(tool: dict) -> str | None:
    """
    Adjust here if the field name in your dump is different.
    """
    return tool.get("additionDate")


def summarize_addition_dates(tools: list[dict]) -> dict:
    parsed = []
    missing = 0
    unparsed = 0

    by_year = Counter()
    by_year_month = Counter()

    for tool in tools:
        raw_date = extract_addition_date(tool)

        if raw_date is None:
            missing += 1
            continue

        dt = parse_date(raw_date)
        if dt is None:
            unparsed += 1
            continue

        parsed.append(
            {
                "name": tool.get("name"),
                "biotoolsID": tool.get("biotoolsID"),
                "additionDate": raw_date,
                "parsed_date": dt,
            }
        )

        by_year[str(dt.year)] += 1
        by_year_month[dt.strftime("%Y-%m")] += 1

    parsed_sorted = sorted(parsed, key=lambda x: x["parsed_date"])

    def strip_parsed_date(row: dict) -> dict:
        return {
            "name": row["name"],
            "biotoolsID": row["biotoolsID"],
            "additionDate": row["additionDate"],
        }

    total = len(tools)
    parsed_count = len(parsed_sorted)

    summary = {
        "total": total,
        "with_parsable_addition_date": parsed_count,
        "missing_addition_date": missing,
        "unparsed_addition_date": unparsed,
        "earliest": strip_parsed_date(parsed_sorted[0]) if parsed_sorted else None,
        "latest": strip_parsed_date(parsed_sorted[-1]) if parsed_sorted else None,
        "oldest_10": [strip_parsed_date(x) for x in parsed_sorted[:10]],
        "newest_10": [strip_parsed_date(x) for x in parsed_sorted[-10:]],
        "by_year": dict(sorted(by_year.items())),
        "by_year_month": dict(sorted(by_year_month.items())),
    }

    return summary


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

    biotools_only_summary = summarize_addition_dates(biotools_only_full)
    remaining_summary = summarize_addition_dates(remaining_tools)

    combined = {
        "biotools_only": biotools_only_summary,
        "remaining_tools": remaining_summary,
        "not_found_count": len(not_found),
    }

    print(json.dumps(combined, indent=2, ensure_ascii=False))

    save_json(biotools_only_full, OUTPUT_DIR / "biotools_only_full_tools.json")
    save_json(not_found, OUTPUT_DIR / "biotools_only_not_found.json")
    save_json(biotools_only_summary, OUTPUT_DIR / "biotools_only_addition_date_summary.json")
    save_json(remaining_summary, OUTPUT_DIR / "remaining_tools_addition_date_summary.json")
    save_json(combined, OUTPUT_DIR / "addition_date_comparison.json")


if __name__ == "__main__":
    main()