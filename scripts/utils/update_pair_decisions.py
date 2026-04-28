"""
Update pair_decisions.jsonl with human pair decisions.

It reads:
- human_annotations/human_conflicts_log.jsonl
- src/application/services/integration/disambiguation/pair_decisions.jsonl

And updates pair_decisions.jsonl using pair_id as the unique key.

Behavior:
- If a human pair decision is not present in pair_decisions.jsonl, it is added.
- If a human pair decision is already present, the existing record is updated
  with the decision found in the human logs file.

Expected mapping:
- decision == "same"      -> same_as_remaining = True
- decision == "different" -> same_as_remaining = False
- decision == "unclear"   -> same_as_remaining = True, confidence = "very-low"

Notes:
- The output schema preserves the existing key name "same_as_remaining"
  because that is what already exists in pair_decisions.jsonl.
- The original human decision is also stored as "decision".
- Only records with kind == "pair" are considered.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


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


def write_jsonl(path: Path, records: list[dict]) -> int:
    """
    Rewrite a JSONL file with the provided records.

    Returns the number of written records.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return len(records)


def decision_to_bool_and_confidence(
    decision: str,
    confidence: str | None,
) -> tuple[bool, str]:
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

    decision = (human_record.get("decision") or "").strip().lower()

    same_as_remaining, output_confidence = decision_to_bool_and_confidence(
        decision,
        human_record.get("confidence"),
    )

    transformed = {
        "pair_id": pair_id,
        "kind": "pair",
        "decision": decision,
        "same_as_remaining": same_as_remaining,
        "confidence": output_confidence,
        "source": human_record.get("source", "human"),
        "ts": human_record.get("ts"),
    }

    return transformed


def merge_existing_record(existing_record: dict, human_record: dict) -> dict:
    """
    Update an existing pair_decisions record with the human decision fields.

    Existing extra fields are preserved unless they are explicitly replaced
    by the transformed human record.
    """
    transformed = transform_human_record(human_record)

    updated_record = {
        **existing_record,
        **transformed,
    }

    return updated_record


def update_pair_decisions(
    human_logs_path: Path,
    pair_decisions_path: Path,
) -> tuple[int, int, int, int]:
    """
    Add or update human pair decisions in pair_decisions.jsonl.

    Returns:
        (
            total_human_pair_records,
            added_count,
            updated_count,
            final_record_count,
        )
    """
    human_records = load_jsonl(human_logs_path)

    existing_records = []
    if pair_decisions_path.exists():
        existing_records = load_jsonl(pair_decisions_path)

    existing_pair_index = {
        record.get("pair_id"): index
        for index, record in enumerate(existing_records)
        if record.get("kind") == "pair" and record.get("pair_id")
    }

    total_human_pair_records = 0
    added_count = 0
    updated_count = 0

    # If the human log contains duplicate pair_ids, the last one wins.
    human_pair_records_by_id: dict[str, dict] = {}

    for human_record in human_records:
        if human_record.get("kind") != "pair":
            continue

        total_human_pair_records += 1

        pair_id = human_record.get("pair_id")
        if not pair_id:
            print(f"Skipping human record without pair_id: {human_record}")
            continue

        human_pair_records_by_id[pair_id] = human_record

    for pair_id, human_record in human_pair_records_by_id.items():
        if pair_id in existing_pair_index:
            index = existing_pair_index[pair_id]
            existing_records[index] = merge_existing_record(
                existing_record=existing_records[index],
                human_record=human_record,
            )
            updated_count += 1
        else:
            transformed = transform_human_record(human_record)
            existing_records.append(transformed)
            existing_pair_index[pair_id] = len(existing_records) - 1
            added_count += 1

    final_record_count = write_jsonl(pair_decisions_path, existing_records)

    return total_human_pair_records, added_count, updated_count, final_record_count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Add or update human pair decisions in pair_decisions.jsonl."
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

    total_human, added, updated, final_count = update_pair_decisions(
        human_logs_path=human_logs_path,
        pair_decisions_path=pair_decisions_path,
    )

    print("Update completed.")
    print(f"Human pair records found: {total_human}")
    print(f"Added to pair_decisions.jsonl: {added}")
    print(f"Updated in pair_decisions.jsonl: {updated}")
    print(f"Final records in pair_decisions.jsonl: {final_count}")


if __name__ == "__main__":
    main()