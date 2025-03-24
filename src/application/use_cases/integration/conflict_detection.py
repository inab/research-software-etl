import json
from src.application.services.integration.conflict_detection import find_disconnected_entries


def detect_conflicts(grouped_entries_file, disconnected_entries_file):
    with open(grouped_entries_file, "r", encoding="utf-8") as f:
        grouped_entries = json.load(f)
    
    disconnected_entries = find_disconnected_entries(grouped_entries)
    print(f"{len(disconnected_entries)} conflictive keys found.")

    with open(disconnected_entries_file, "w", encoding="utf-8") as f:
        json.dump(disconnected_entries, f, indent=4)

