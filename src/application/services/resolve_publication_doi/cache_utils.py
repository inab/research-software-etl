from __future__ import annotations

import json
from pathlib import Path


def ensure_parent_dir(file_path: str) -> None:
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)


def load_seen_document_ids(
    resolved_path: str = "data/cache/resolved_dois.jsonl",
    unresolved_path: str = "data/cache/unresolved_dois.jsonl",
) -> set[str]:
    seen: set[str] = set()

    for file_path in (resolved_path, unresolved_path):
        path = Path(file_path)
        if not path.exists():
            continue

        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                document_id = record.get("document_id")
                if document_id:
                    seen.add(str(document_id))

    return seen


def append_jsonl_record(file_path: str, record: dict) -> None:
    ensure_parent_dir(file_path)
    with Path(file_path).open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")