#!/usr/bin/env python3
"""
Normalize JSONL records for human conflict decisions.

Fixes records where:
- "decision" is incorrectly nested as an object
- "date" should be stored as "ts"
- "kind" is missing (set to "pair")
- "source" is missing (set to "human")

Example wrong record:
{
  "pair_id": "...",
  "date": "2026-03-31T10:36:52.807781+00:00",
  "conflict_name": "...",
  "conflict_url": "...",
  "decision": {
    "decision": "unclear",
    "explanation": "No info",
    "confidence": "low",
    "issue_url": "..."
  }
}

Becomes:
{
  "pair_id": "...",
  "ts": "2026-03-31 10:36:52.807781",
  "conflict_name": "...",
  "conflict_url": "...",
  "decision": "unclear",
  "explanation": "No info",
  "confidence": "low",
  "issue_url": "...",
  "kind": "pair",
  "source": "human"
}
"""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def normalize_timestamp(value: str) -> str:
    """
    Convert ISO datetime strings like:
        2026-03-31T10:36:52.807781+00:00
    into:
        2026-03-31 10:36:52.807781

    If parsing fails, return the original value unchanged.
    """
    if not isinstance(value, str):
        return value

    try:
        dt = datetime.fromisoformat(value)
        return dt.replace(tzinfo=None).isoformat(sep=" ")
    except ValueError:
        return value


def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a single record to the expected schema as much as possible.
    """
    original = deepcopy(record)
    normalized: Dict[str, Any] = {}

    nested_decision = (
        original.get("decision")
        if isinstance(original.get("decision"), dict)
        else None
    )

    for key, value in original.items():
        # Expand nested decision object into top-level fields
        if key == "decision" and isinstance(value, dict):
            normalized["decision"] = value.get("decision")
            if "explanation" not in original:
                normalized["explanation"] = value.get("explanation", "")
            if "confidence" not in original:
                normalized["confidence"] = value.get("confidence", "")
            if "issue_url" not in original:
                normalized["issue_url"] = value.get("issue_url", "")
            continue

        # Rename date -> ts
        if key == "date":
            if "ts" not in original:
                normalized["ts"] = normalize_timestamp(value)
            continue

        normalized[key] = value

    # If decision was not nested, ensure related fields exist if already top-level
    if nested_decision is None:
        normalized.setdefault("decision", original.get("decision"))
        if "explanation" in original:
            normalized["explanation"] = original["explanation"]
        if "confidence" in original:
            normalized["confidence"] = original["confidence"]
        if "issue_url" in original:
            normalized["issue_url"] = original["issue_url"]

    # Fill defaults required by your schema
    normalized.setdefault("kind", "pair")
    normalized.setdefault("source", "human")

    return normalized


def process_jsonl(input_path: Path, output_path: Path) -> tuple[int, int]:
    """
    Read input JSONL, normalize each record, and write output JSONL.

    Returns:
        total_records, changed_records
    """
    total_records = 0
    changed_records = 0

    with input_path.open("r", encoding="utf-8") as infile, output_path.open(
        "w", encoding="utf-8"
    ) as outfile:
        for line_number, line in enumerate(infile, start=1):
            stripped = line.strip()

            if not stripped:
                outfile.write("\n")
                continue

            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number}: {exc}"
                ) from exc

            total_records += 1
            normalized = normalize_record(record)

            if normalized != record:
                changed_records += 1

            outfile.write(json.dumps(normalized, ensure_ascii=False) + "\n")

    return total_records, changed_records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Normalize malformed human decision JSONL records."
    )
    parser.add_argument("input_jsonl", type=Path, help="Input JSONL file")
    parser.add_argument("output_jsonl", type=Path, help="Output JSONL file")
    args = parser.parse_args()

    total, changed = process_jsonl(args.input_jsonl, args.output_jsonl)

    print(f"Processed {total} records")
    print(f"Normalized {changed} records")
    print(f"Output written to: {args.output_jsonl}")


if __name__ == "__main__":
    main()