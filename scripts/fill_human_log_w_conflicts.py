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
def stable_hash(obj) -> str:
    canonical = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
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


def make_hash(o):

  """
  Makes a hash from a dictionary, list, tuple or set to any level, that contains
  only other hashable types (including any lists, tuples, sets, and
  dictionaries).
  """

  if isinstance(o, (set, tuple, list)):

    return tuple([make_hash(e) for e in o])    

  elif not isinstance(o, dict):

    return hash(o)

  new_o = copy.deepcopy(o)
  for k, v in new_o.items():
    new_o[k] = make_hash(v)

  return hash(tuple(frozenset(sorted(new_o.items()))))


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

            conflict_id, payload = next(iter(obj.items()))

            if not isinstance(payload, dict):
                raise ValueError(
                    f"[human] Expected object value for '{conflict_id}' "
                    f"on line {lineno}, got: {type(payload)}"
                )

            conflict_block = blocks.get(conflict_id)
            if conflict_block is None:
                missing += 1
                print(
                    f"[human] WARNING: conflict id '{conflict_id}' "
                    f"not found in conflict blocks; setting conflict=null",
                    file=sys.stderr,
                )
                
                #payload['date'] = datetime.datetime.now()
                #payload['conflict_name'] = conflict_id
                #payload['conflict_id'] = f"{conflict_id}_NONE"
                #payload["conflict"] = None
                #payload["conflict"] = conflict_block

            else:
                payload['date'] = datetime.datetime.now()
                payload['conflict_name'] = conflict_id
                payload['conflict_id'] = f"{conflict_id}_{stable_hash(conflict_block)}"
                payload['conflict'] = conflict_block

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