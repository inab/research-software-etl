"""
Update pair_decisions.jsonl with missing human pair decisions.

It reads:
- human_annotations/human_conflicts_logs.jsonl
- src/application/services/integration/disambiguation/pair_decisions.jsonl

And appends to pair_decisions.jsonl any human pair decisions that are not already
present there, using pair_id as the unique key.

Expected mapping:
- decision == "same"      -> same_as_remaining = True
- decision == "different" -> same_as_remaining = False
- decision == "unclear"   -> same_as_remaining = True, confidence = "very-low"

Notes:
- The output schema preserves the existing key name "same_as_remaining"
  because that is what already exists in pair_decisions.jsonl.
- Only records with kind == "pair" are considered.
- Existing pair_ids in pair_decisions.jsonl are never overwritten.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable


def load_jsonl(path: Path) -> list[dict]:
    """
    Load a JSONL file into a list of dictionaries.

    Empty lines are ignored.
    """
    records = []

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {path} at line {line_number}: {exc}"
                ) from exc

    return records


def append_jsonl(path: Path, records: Iterable[dict]) -> int:
    """
    Append records to a JSONL file.

    Returns the number of appended records.
    """
    count = 0

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    return count


def decision_to_bool_and_confidence(decision: str, confidence: str | None) -> tuple[bool, str]:
    """
    Convert the human decision into:
    - the boolean expected by pair_decisions.jsonl
    - the confidence to store

    Rules:
    - same      -> True, keep original confidence
    - different -> False, keep original confidence
    - unclear   -> True, force confidence to "very-low"
    """
    normalized_decision = (decision or "").strip().lower()
    normalized_confidence = (confidence or "").strip()

    if normalized_decision == "same":
        return True, normalized_confidence

    if normalized_decision == "different":
        return False, normalized_confidence

    if normalized_decision == "unclear":
        return True, "very-low"

    raise ValueError(
        f"Unexpected decision value: {decision!r}. "
        f"Expected 'same', 'different', or 'unclear'."
    )


def transform_human_record(human_record: dict) -> dict:
    """
    Transform one human annotation record into the pair_decisions.jsonl schema.
    """
    pair_id = human_record.get("pair_id")
    if not pair_id:
        raise ValueError(f"Human record missing pair_id: {human_record}")

    if human_record.get("kind") != "pair":
        raise ValueError(f"Human record is not kind='pair': {human_record}")

    same_as_remaining, output_confidence = decision_to_bool_and_confidence(
        human_record.get("decision"),
        human_record.get("confidence"),
    )

    transformed = {
        "pair_id": pair_id,
        "kind": "pair",
        "same_as_remaining": same_as_remaining,
        "confidence": output_confidence,
        "source": human_record.get("source", "human"),
        "ts": human_record.get("ts"),
    }

    return transformed


def update_pair_decisions(
    human_logs_path: Path,
    pair_decisions_path: Path,
) -> tuple[int, int, int]:
    """
    Append missing human pair decisions to pair_decisions.jsonl.

    Returns:
        (
            total_human_pair_records,
            already_present_count,
            appended_count,
        )
    """
    human_records = load_jsonl(human_logs_path)

    existing_records = []
    if pair_decisions_path.exists():
        existing_records = load_jsonl(pair_decisions_path)

    existing_pair_ids = {
        record.get("pair_id")
        for record in existing_records
        if record.get("kind") == "pair" and record.get("pair_id")
    }

    records_to_append = []
    total_human_pair_records = 0
    already_present_count = 0

    # Prevent duplicates inside the same human log file
    seen_new_pair_ids = set()

    for human_record in human_records:
        if human_record.get("kind") != "pair":
            continue

        total_human_pair_records += 1
        pair_id = human_record.get("pair_id")

        if not pair_id:
            print(f"Skipping human record without pair_id: {human_record}")
            continue

        if pair_id in existing_pair_ids:
            already_present_count += 1
            continue

        if pair_id in seen_new_pair_ids:
            continue

        transformed = transform_human_record(human_record)
        records_to_append.append(transformed)
        seen_new_pair_ids.add(pair_id)

    appended_count = append_jsonl(pair_decisions_path, records_to_append)

    return total_human_pair_records, already_present_count, appended_count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Append missing human pair decisions to pair_decisions.jsonl."
    )
    parser.add_argument(
        "--human-logs",
        default="human_annotations/human_conflicts_log.jsonl",
        help="Path to the human conflicts log JSONL file.",
    )
    parser.add_argument(
        "--pair-decisions",
        default="src/application/services/integration/disambiguation/pair_decisions.jsonl",
        help="Path to the target pair_decisions.jsonl file.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    human_logs_path = Path(args.human_logs)
    pair_decisions_path = Path(args.pair_decisions)

    total_human, already_present, appended = update_pair_decisions(
        human_logs_path=human_logs_path,
        pair_decisions_path=pair_decisions_path,
    )

    print("Update completed.")
    print(f"Human pair records found: {total_human}")
    print(f"Already present in pair_decisions.jsonl: {already_present}")
    print(f"Appended: {appended}")


if __name__ == "__main__":
    main()