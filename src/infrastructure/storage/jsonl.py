from __future__ import annotations

from pathlib import Path
import json


class JsonlPublicationEnrichmentCache:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def load_seen_dois(self) -> set[str]:
        seen_dois: set[str] = set()

        if not self.path.exists():
            return seen_dois

        with self.path.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    item = json.loads(line)
                except json.JSONDecodeError as exc:
                    print(
                        f"Warning: could not parse JSONL line {line_number} "
                        f"in {self.path}: {exc}"
                    )
                    continue

                doi = item.get("doi")
                if isinstance(doi, str) and doi.strip():
                    seen_dois.add(doi.strip().lower())

        return seen_dois

    def append(self, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")