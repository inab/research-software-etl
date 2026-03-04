from __future__ import annotations

import json
from typing import Any, Dict, Iterable, Optional, Tuple


def _canonicalize(obj: Any) -> Any:
    """
    Convert arbitrary JSON-like objects into a canonical, order-insensitive form.

    - dicts: keys sorted, values canonicalized
    - lists: elements canonicalized and then sorted by a stable representation
    - scalars: unchanged
    """
    if isinstance(obj, dict):
        return tuple((k, _canonicalize(obj[k])) for k in sorted(obj.keys()))
    if isinstance(obj, list):
        canon_elems = [_canonicalize(x) for x in obj]
        # sort list elements in an order-insensitive way
        return tuple(sorted(canon_elems, key=_stable_repr))
    return obj


def _stable_repr(obj: Any) -> str:
    """
    Stable string representation used for sorting canonicalized list elements.
    """
    # obj here is already canonicalized (dicts->tuples, lists->tuples), so repr is stable enough
    return repr(obj)


def _conflict_signature(conflict_block: Dict[str, Any]) -> Any:
    """
    Signature for matching conflicts by content.
    Assumes conflict_block looks like: {"remaining":[...], "disconnected":[...]} (order-insensitive).
    """
    if not isinstance(conflict_block, dict):
        raise ValueError(f"conflict_block must be a dict, got {type(conflict_block)}")

    # Only compare on the content that defines the conflict.
    # If your conflict blocks contain extra keys in the future, this still works.
    remaining = conflict_block.get("remaining", [])
    disconnected = conflict_block.get("disconnected", [])

    normalized = {
        "remaining": remaining,
        "disconnected": disconnected,
    }
    return _canonicalize(normalized)


def find_previous_annotation_for_conflict(
    conflict_block: Dict[str, Any],
    manual_logs: str,
    *,
    require_decision: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Search manual annotation logs (JSONL) for a previously solved conflict with identical content.

    Each log line is expected to be a JSON object with exactly one top-level key:
      {"<conflict_id>": {"decision": "...", ..., "conflict": {...}}}

    Matching is done on the CONTENT of the "conflict" field, ignoring order of keys and list items.

    Returns:
      - the annotation payload dict (e.g., {"decision":..., "explanation":..., ...}) from the first match found
      - None if no match is found

    Notes:
      - If a log entry lacks "conflict", it is skipped.
      - If require_decision=True, entries without a non-empty "decision" are ignored.
    """
    target_sig = _conflict_signature(conflict_block)

    with open(manual_logs, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                # skip bad lines; you can change to raise if you prefer strictness
                continue

            if not isinstance(obj, dict) or len(obj) != 1:
                continue

            _, payload = next(iter(obj.items()))
            if not isinstance(payload, dict):
                continue

            if require_decision and not str(payload.get("decision", "")).strip():
                continue

            logged_conflict = payload.get("conflict")
            if not isinstance(logged_conflict, dict):
                # no embedded conflict content to compare against
                continue

            logged_sig = _conflict_signature(logged_conflict)
            if logged_sig == target_sig:
                # Return the annotation payload (optionally you might want to drop "conflict")
                return payload

    return None