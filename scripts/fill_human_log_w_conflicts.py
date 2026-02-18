#!/usr/bin/env python3
"""
Fill a "conflict" field in each entry of a human conflicts log JSONL file,
by matching the entry key (conflict id) against a conflict blocks JSONL file.

Input formats (one JSON object per line, single top-level key per line):
- human_conflicts_log.jsonl:
  {"beagle/cmd": {"decision": "...", ...}}
- conflict_blocks_0.4.jsonl:
  {"beagle/cmd": {"remaining": [...], "disconnected": [...]}}

Output:
- same as human log, but with {"conflict": <matched block>} added inside the value dict
"""

from __future__ import annotations

import json
import sys
import copy
import hashlib
from pprint import pprint
import datetime
from typing import Any, Dict, Iterable

# ---------------------------------------------------------------------
# Hardcoded paths
# ---------------------------------------------------------------------

HUMAN_LOG_PATH = "/Users/evabsc/projects/software-observatory/research-software-etl/human_annotations/human_conflicts_log.jsonl"
CONFLICT_BLOCKS_PATHS = [
    "/Users/evabsc/projects/software-observatory/research-software-etl/scripts/data/conflict_blocks.jsonl",
    "/Users/evabsc/projects/software-observatory/research-software-etl/scripts/data/conflict_blocks_0.2.jsonl",
    "/Users/evabsc/projects/software-observatory/research-software-etl/scripts/data/conflict_blocks_0.3.jsonl",
    "/Users/evabsc/projects/software-observatory/research-software-etl/scripts/data/conflict_blocks_0.4.jsonl"
    ]
OUTPUT_PATH = "/Users/evabsc/projects/software-observatory/research-software-etl/human_annotations/human_conflicts_log.filled.jsonl"


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _canonical_dumps(obj: Any) -> str:
    # Canonical JSON string used only for sorting + hashing
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def _normalize(obj: Any) -> Any:
    """
    Normalize JSON-like data so that:
      - dict keys are sorted (handled by canonical dumps)
      - list order is ignored (lists treated as multisets)
    """
    if isinstance(obj, dict):
        # normalize values; keep keys as-is (sorting happens in dumps)
        return {k: _normalize(v) for k, v in obj.items()}

    if isinstance(obj, list):
        norm_items = [_normalize(x) for x in obj]

        # Sort by (type, canonical-json) to make ordering deterministic even for mixed types.
        # Using type name avoids comparing unlike Python objects directly.
        return sorted(
            norm_items,
            key=lambda x: (type(x).__name__, _canonical_dumps(x))
        )

    # JSON scalars (str/int/float/bool/None) are already stable
    return obj


def extract_ids(obj):
    if len(obj['remaining'])>0:
        new_obj = {
            'remaining' : normalize_ids(obj['remaining'][0]['id']),
            'disconnected': obj['disconnected'][0]['id']
        }
    else:
        new_obj = {
            'remaining' : obj['disconnected'][0]['id'],
            'disconnected': obj['disconnected'][1]['id']
        }
        
    return new_obj

def normalize_ids(original_id):
    individual_ids = original_id.split(',')
    individual_ids.sort()
    result = ",".join(individual_ids)
    return result

def stable_hash(obj: Any) -> str:
    obj = extract_ids(obj)
    normalized = _normalize(obj)
    canonical = _canonical_dumps(normalized)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()



def load_conflict_blocks(paths: Iterable[str]) -> Dict[str, Any]:
    """
    Load conflict blocks from multiple JSONL files into a single dict keyed by conflict id.

    Each line must be a JSON object with exactly one top-level key:
      {"some/id": {...block...}}

    Duplicate conflict ids across files:
      - keeps the first occurrence encountered
      - prints a warning for subsequent occurrences
    """
    blocks: Dict[str, Any] = {}

    for path in paths:
        with open(path, "r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    raise ValueError(f"[blocks] Invalid JSON in {path} on line {lineno}: {e}") from e

                if not isinstance(obj, dict) or len(obj) != 1:
                    raise ValueError(
                        f"[blocks] Expected exactly one top-level key in {path} on line {lineno}, got: {obj!r}"
                    )

                conflict_id, conflict_block = next(iter(obj.items()))

                if conflict_id in blocks:
                    print(
                        f"[blocks] WARNING: duplicate conflict id '{conflict_id}' "
                        f"in file {path} line {lineno}; keeping first occurrence",
                        file=sys.stderr,
                    )
                    continue

                blocks[conflict_id] = conflict_block

    return blocks



# ---------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------

def fill_human_conflicts() -> None:
    blocks = load_conflict_blocks(CONFLICT_BLOCKS_PATHS)

    total = 0
    missing = 0

    with open(HUMAN_LOG_PATH, "r", encoding="utf-8") as fin, \
         open(OUTPUT_PATH, "w", encoding="utf-8") as fout:

        for lineno, line in enumerate(fin, start=1):
            line = line.strip()
            if not line:
                continue

            total += 1

            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"[human] Invalid JSON on line {lineno}: {e}") from e

            if not isinstance(obj, dict) or len(obj) != 1:
                raise ValueError(
                    f"[human] Expected exactly one top-level key on line {lineno}, got: {obj!r}"
                )

            pair_id, payload = next(iter(obj.items()))

            if not isinstance(payload, dict):
                raise ValueError(
                    f"[human] Expected object value for '{pair_id}' "
                    f"on line {lineno}, got: {type(payload)}"
                )

            conflict_block = blocks.get(pair_id)
            if conflict_block is None:
                missing += 1
                print(
                    f"[human] WARNING: conflict pair id '{pair_id}' "
                    f"not found in conflict blocks; setting conflict=null",
                    file=sys.stderr,
                )

            else:
                #pprint(conflict_block)
                payload['ts'] = datetime.datetime.now()
                payload['conflict_name'] = pair_id
                payload['pair_id'] = f"p:{pair_id}_{stable_hash(conflict_block)}"
                #payload['pair_id'] = f"p:{pair_id}"
                payload['conflict'] = conflict_block
                payload['kind'] = 'pair'
                payload['source'] = 'human'


            json.dump(payload, fout, ensure_ascii=False, default=str)
            fout.write("\n")

    print(
        f"Done. Wrote {total} entries to '{OUTPUT_PATH}'. "
        f"Missing conflict blocks for {missing} entries.",
        file=sys.stderr,
    )


# ---------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------

if __name__ == "__main__":
    fill_human_conflicts()