import json
from application.services.integration.conflict_detection import find_disconnected_entries


def detect_conflicts(grouped_entries_file, disconnected_entries_file, url_checker):
    with open(grouped_entries_file, "r", encoding="utf-8") as f:
        grouped_entries = json.load(f)

    print(f"Number of blocks: {len(grouped_entries)}")
    print(f"Number of instances: {sum(len(block['instances']) for block in grouped_entries.values())}")

    conflict_blocks = find_disconnected_entries(
        grouped_entries, url_checker, use_name_match_for_no_links=False
    )
    print(f"{len(conflict_blocks)} conflictive keys found.")

    with open(disconnected_entries_file, "w", encoding="utf-8") as f:
        json.dump(conflict_blocks, f, indent=4)

