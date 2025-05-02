import json
from src.application.services.integration.conflict_detection import find_disconnected_entries, apply_source_name_merge


def detect_conflicts(grouped_entries_file, disconnected_entries_file):
    with open(grouped_entries_file, "r", encoding="utf-8") as f:
        grouped_entries = json.load(f)

    print(f"Number of blocks: {len(grouped_entries)}")
    print(f"Number of instances: {sum(len(block['instances']) for block in grouped_entries.values())}")
    
    #conflict_blocks = find_disconnected_entries(grouped_entries)
    conflict_blocks = find_disconnected_entries(grouped_entries, use_name_match_for_no_links=False)
    conflict_blocks = apply_source_name_merge(conflict_blocks)
    print(f"{len(conflict_blocks)} conflictive keys found.")

    with open(disconnected_entries_file, "w", encoding="utf-8") as f:
        json.dump(conflict_blocks, f, indent=4)

