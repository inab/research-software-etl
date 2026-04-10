from application.services.integration.disambiguation.results import build_disambiguated_record_after_human
from application.services.integration.disambiguation.utils import load_dict_from_jsonl, update_jsonl_record
import json


import json
import re


def load_jsonl_as_list(file_path):
    """
    Load a JSONL file as a list of records.
    Skips empty lines.
    """
    records = []

    with open(file_path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {file_path} at line {line_number}: {exc}"
                ) from exc

    return records


def extract_issue_url_from_notes(notes):
    """
    Extract the GitHub issue URL from a notes string.

    Example:
    'Manual review needed. Issue URL: https://github.com/inab/research-software-etl/issues/1032'
    """
    if not notes or not isinstance(notes, str):
        return None

    match = re.search(
        r"https://github\.com/inab/research-software-etl/issues/\d+",
        notes
    )
    return match.group(0) if match else None


def index_human_annotations_by_issue_url(human_annotations):
    """
    Build a lookup dict from a list of human annotation records:
        {issue_url: annotation_record}
    """
    indexed = {}

    for record in human_annotations:
        if not isinstance(record, dict):
            continue

        issue_url = record.get("issue_url")
        if issue_url:
            indexed[issue_url] = record

    return indexed


def run_disambiguation_after_human_annotation(
    conflict_blocks_file,
    disambiguated_blocks_file
):
    print("Starting update of disambiguated blocks after human resolution....")

    # Load input data
    disambiguated_blocks = load_dict_from_jsonl(disambiguated_blocks_file)
    conflict_blocks = load_dict_from_jsonl(conflict_blocks_file)

    # Load human annotations as a list of records
    human_log_path = "human_annotations/human_conflicts_log.jsonl"
    human_annotations = load_jsonl_as_list(human_log_path)
    human_by_issue_url = index_human_annotations_by_issue_url(human_annotations)

    conflicts_updated = 0
    not_found = []

    for conflict_id, block in disambiguated_blocks.items():
        if block.get("resolution") != "manual_review_pending":
            continue

        notes = block.get("notes", "")
        issue_url = extract_issue_url_from_notes(notes)

        if not issue_url:
            print(f"Could not extract issue URL from notes for {conflict_id}")
            not_found.append(conflict_id)
            continue

        decision = human_by_issue_url.get(issue_url)

        if decision:
            conflict = conflict_blocks.get(conflict_id)

            if conflict is None:
                print(f"Conflict block not found for {conflict_id}")
                not_found.append(conflict_id)
                continue

            record = build_disambiguated_record_after_human(
                conflict_id,
                conflict,
                decision
            )

            update_jsonl_record(disambiguated_blocks_file, conflict_id, record)
            conflicts_updated += 1

        else:
            print(f"Could not find human decision for {conflict_id}")
            print(f"Issue URL searched: {issue_url}")
            not_found.append(conflict_id)

    print(f"Total conflicts updated: {conflicts_updated}")
    print(f"Total conflicts not found in human annotations: {len(not_found)}")
    print(f"List of conflicts not found in human annotations: {not_found}")