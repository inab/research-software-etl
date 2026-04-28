from datetime import datetime
from pprint import pprint

def generate_merge_note_if_needed(merged_ids):
    """
   
    """

    # Extract name from _id assuming format: <source>/<name>/<type><version>
    def parse_name_from_id(entry_id):
        try:
            return entry_id.split("/")[1]
        except IndexError:
            return entry_id

    name_set = set()

    for id in merged_ids:
        name = parse_name_from_id(id)
        if name:
            name_set.add(name)

    if len(name_set) > 1:
        return "Caution: merged entries have different names. May be distinct software."

    else:
        return ''


from collections import Counter
from datetime import datetime


def build_disambiguated_record(
    block_id,
    block,
    pair_results,
    model_name="auto:agreement-proxy-v",
):
    """
    Builds a structured resolution record for a disambiguation block.

    This version supports mixed-origin pairwise decisions within the same block
    and correctly preserves human "unclear" decisions.

    Important:
    - Do not infer "unclear" from same_as_remaining.
    - Human unclear decisions are stored as same_as_remaining=True for backward
      compatibility, so the original "decision" field must be used.
    """

    def _normalize_remaining_ids(raw_remaining):
        """
        Accept either:
        - comma-separated string of ids
        - single id string
        - list of ids
        - fallback to block['remaining']
        """
        if raw_remaining is None:
            return [entry["id"] for entry in block.get("remaining", [])]

        if isinstance(raw_remaining, list):
            return raw_remaining

        if isinstance(raw_remaining, str):
            if "," in raw_remaining:
                return [x.strip() for x in raw_remaining.split(",") if x.strip()]
            return [raw_remaining.strip()]

        return [entry["id"] for entry in block.get("remaining", [])]

    def _normalize_source(source, decision):
        """
        Normalize source labels for pairwise_summary.

        Human unclear must be detected from decision == "unclear",
        not from same_as_remaining.
        """
        normalized_source = (source or "").strip().lower()
        normalized_decision = (decision or "").strip().lower()

        if normalized_source in {"llm", "proxy", "auto", "agreement_proxy"}:
            return "llm"

        if normalized_source == "human":
            if normalized_decision == "unclear":
                return "human_unclear"
            return "human"

        if normalized_source == "human_unclear":
            return "human_unclear"

        if not normalized_source:
            return "unknown"

        return normalized_source

    if len(pair_results) == 0:
        merged_ids = [entry["id"] for entry in block.get("remaining", [])]
        unmerged_ids = []
        unclear_entries = []
        confidence_scores = {}
        pair_decisions = []

        note = "All entries grouped heuristically or by shared metadata. No disambiguation needed."

        pair_source_counts = {
            "total_pairs": 0,
            "llm": 0,
            "human": 0,
            "human_unclear": 0,
            "unknown": 0,
            "other_sources": {},
        }

        resolution = "no_conflict"

    else:
        merged_ids = _normalize_remaining_ids(pair_results[0].get("remaining_id"))
        unmerged_ids = []
        unclear_entries = []
        confidence_scores = {}
        pair_decisions = []
        note = ""

        source_counter = Counter()

        for res in pair_results:
            disconnected_id = res["disconnected_id"]
            same_as_remaining = res.get("same_as_remaining")
            decision = (res.get("decision") or "").strip().lower()

            confidence_scores[disconnected_id] = res.get("confidence")

            normalized_source = _normalize_source(
                res.get("source"),
                decision,
            )
            source_counter[normalized_source] += 1

            pair_decisions.append({
                "pair_id": res.get("conflict_id"),
                "remaining_id": res.get("remaining_id"),
                "disconnected_id": disconnected_id,
                "decision": decision or None,
                "same_as_remaining": same_as_remaining,
                "confidence": res.get("confidence"),
                "source": res.get("source"),
                "ts": res.get("ts"),
            })

            if decision == "unclear":
                unclear_entries.append(disconnected_id)
            elif same_as_remaining is True:
                merged_ids.append(disconnected_id)
            elif same_as_remaining is False:
                unmerged_ids.append(disconnected_id)
            else:
                unclear_entries.append(disconnected_id)

        pair_source_counts = {
            "total_pairs": len(pair_results),
            "llm": source_counter.get("llm", 0),
            "human": source_counter.get("human", 0),
            "human_unclear": source_counter.get("human_unclear", 0),
            "unknown": source_counter.get("unknown", 0),
            "other_sources": {
                k: v
                for k, v in source_counter.items()
                if k not in {"llm", "human", "human_unclear", "unknown"}
            },
        }

        note += generate_merge_note_if_needed(merged_ids)

        if unclear_entries:
            if note:
                note += " "
            note += (
                f"{len(unclear_entries)} pairwise comparison(s) remained unclear "
                f"after human review."
            )

        if unclear_entries:
            resolution = "partial_unclear"
        elif unmerged_ids:
            resolution = "partial"
        else:
            resolution = "merged"

    if not note:
        note = None
    else:
        note = note.strip()

    record = {
        "resolution": resolution,
        "merged_entries": merged_ids,
        "unmerged_entries": unmerged_ids,
        "unclear_entries": unclear_entries if pair_results else [],
        "source": model_name,
        "confidence_scores": confidence_scores,
        "pairwise_summary": pair_source_counts,
        "pair_decisions": pair_decisions if pair_results else [],
        "timestamp": datetime.now().isoformat(),
        "notes": note,
    }

    return {block_id: record}


def build_disambiguated_record_manual(
    block_id,
    block,
    issue_url,
    model_name="auto:agreement-proxy-v",
):
    merged_ids = [entry["id"] for entry in block.get("remaining", [])]
    unmerged_ids = [entry["id"] for entry in block.get("disconnected", [])]

    record = {
        "resolution": "manual_review_pending",
        "merged_entries": merged_ids,
        "unmerged_entries": unmerged_ids,
        "unclear_entries": [],
        "source": model_name,
        "confidence_scores": {},
        "pairwise_summary": {
            "total_pairs": 0,
            "llm": 0,
            "human": 0,
            "human_unclear": 0,
            "unknown": 0,
            "other_sources": {},
        },
        "timestamp": datetime.now().isoformat(),
        "notes": f"Manual review needed. Issue URL: {issue_url}",
    }

    return {block_id: record}



from datetime import datetime


def build_disambiguated_record_after_human(conflict_id, conflict, decision):
    """
    Build a disambiguated record after a human annotation has been made.

    Expected human decisions:
    - "same"
    - "different"
    - "unclear"

    Notes:
    - This function is typically used for a single human-reviewed pair conflict.
    - It returns a record compatible with the final disambiguation schema,
      including pairwise_summary and unclear_entries.
    """

    # Defensive normalization for pair-like conflicts where "remaining" may be empty
    # and the two entries are both under "disconnected".
    if len(conflict.get("remaining", [])) == 0:
        if len(conflict.get("disconnected", [])) == 2:
            conflict["remaining"] = [conflict["disconnected"][1]]
            conflict["disconnected"] = [conflict["disconnected"][0]]

    if len(conflict.get("remaining", [])) > 0:
        merged_ids = [entry["id"] for entry in conflict.get("remaining", [])]
    else:
        merged_ids = []

    unmerged_ids = []
    unclear_entries = []
    confidence_scores = {}

    issue_url = decision.get("issue_url")
    human_decision = (decision.get("decision") or "").strip().lower()
    pair_id = decision.get("pair_id") or decision.get("conflict_id")

    disconnected_ids = [entry["id"] for entry in conflict.get("disconnected", [])]

    if human_decision == "same":
        merged_ids.extend(disconnected_ids)
        resolution = "merged"
        pairwise_summary = {
            "total_pairs": 1,
            "llm": 0,
            "human": 1,
            "human_unclear": 0,
            "unknown": 0,
            "other_sources": {},
        }

    elif human_decision == "different":
        unmerged_ids.extend(disconnected_ids)
        resolution = "partial"
        pairwise_summary = {
            "total_pairs": 1,
            "llm": 0,
            "human": 1,
            "human_unclear": 0,
            "unknown": 0,
            "other_sources": {},
        }

    elif human_decision == "unclear":
        unclear_entries.extend(disconnected_ids)
        resolution = "unclear"
        pairwise_summary = {
            "total_pairs": 1,
            "llm": 0,
            "human": 0,
            "human_unclear": 1,
            "unknown": 0,
            "other_sources": {},
        }

    else:
        resolution = "manual_review_pending"
        pairwise_summary = {
            "total_pairs": 1,
            "llm": 0,
            "human": 0,
            "human_unclear": 0,
            "unknown": 1,
            "other_sources": {},
        }
        print(
            f"WARNING: Unknown decision: {human_decision}. "
            "Setting resolution to 'manual_review_pending'."
        )

    note = f"Decision made by human annotator in issue {issue_url}. "
    note += generate_merge_note_if_needed(merged_ids)

    if human_decision == "unclear":
        note += " Human annotator marked this comparison as unclear."

    if not note:
        note = None
    else:
        note = note.strip()

    record = {
        "resolution": resolution,
        "merged_entries": merged_ids,
        "unmerged_entries": unmerged_ids,
        "unclear_entries": unclear_entries,
        "source": "human",
        "pair_decisions": [
            {
                "pair_id": pair_id,
                "decision": human_decision or None,
                "same_as_remaining": (
                    True if human_decision in {"same", "unclear"}
                    else False if human_decision == "different"
                    else None
                ),
        "confidence": decision.get("confidence"),
        "source": "human",
        "ts": decision.get("ts"),
    }
],
        "confidence_scores": confidence_scores,
        "pairwise_summary": pairwise_summary,
        "timestamp": datetime.now().isoformat(),
        "notes": note,
    }

    return record
    



def build_no_conflict_record(block_id, block, source="auto:no_conflict"):
    """
    Generate a disambiguated_blocks record for a block with no disconnected entries.
    This assumes all entries are already grouped (e.g., they share a repo or author).
    """

    merged_ids = block.get("instances", [])

    note = generate_merge_note_if_needed(merged_ids)
    note = f"All entries grouped heuristically or by shared metadata. No disambiguation needed. {note}"
    note = note.strip() # strip leading and trailing whitespace

    return {
        block_id: {
            "resolution": "no_conflict",
            "merged_entries": merged_ids,
            "unmerged_entries": [],
            "source": source,
            "confidence_scores": {},
            "timestamp": datetime.now().isoformat(),
            "notes": note
        }
    }
