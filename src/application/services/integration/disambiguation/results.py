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


def build_disambiguated_record(block_id, block, pair_results, model_name="auto:agreement-proxy-v"):

    """
    Builds a structured resolution record for a disambiguation block.

    This function summarizes the results of pairwise comparisons between disconnected entries
    and a group of known related entries ("remaining") for a given block. It determines which
    disconnected entries should be merged, which remain separate, and stores the associated
    confidence scores.

    Parameters:
    ----------
    block_id : str
        The identifier of the disambiguation block (typically the group key).
    block : dict
        The full conflict block containing "remaining" entries (considered same) and "disconnected" entries (to test).
    pair_results : list of dict
        Each dict contains:
            - "disconnected_id": str
            - "same_as_remaining": bool
            - "confidence": float (from 0 to 1)
    model_name : str, optional
        The source of the decision (e.g., model name). Default is "auto:agreement-proxy-v".

    Returns:
    -------
    dict
        A single-entry dictionary with the block_id as key and the resolution record as value.
        The record includes merged and unmerged IDs, confidence scores, source, timestamp, and resolution type.

    Example:
    -------
    >>> block_id = "toolX/cmd"
    >>> block = {
            "remaining": [{"_id": "id1"}, {"_id": "id2"}],
            "disconnected": [{"_id": "id3"}, {"_id": "id4"}]
        }
    >>> pair_results = [
            {"disconnected_id": "id3", "same_as_remaining": True, "confidence": "high"},
            {"disconnected_id": "id4", "same_as_remaining": False, "confidence": "medium"}
        ]
    >>> build_disambiguated_record(block_id, block, pair_results)
    {
        "toolX/cmd": {
            "resolution": "partial",
            "merged_entries": ["id1", "id2", "id3"],
            "unmerged_entries": ["id4"],
            "source": "auto:agreement-proxy-v",
            "confidence_scores": {
                "id3": "high",
                "id4": "medium"
            },
            "timestamp": "2025-04-28T15:00:00.000Z",
            "notes": None
        }
    }
    """
    #print(f"PAIR RESULTS:")
    #pprint(pair_results)

    #print("BLOCK:")
    #pprint(block)

    if len(pair_results) == 0:        
        merged_ids = [entry["id"] for entry in block.get("remaining", [])]
        unmerged_ids = []
        confidence_scores = {}
        note = 'All entries grouped heuristically or by shared metadata. No disambiguation needed. '
    else:
        remaining_ids_in_pairs = pair_results[0]['remaining_id']
        #merged_ids = [entry["_id"] for entry in block.get("remaining", [])]
        merged_ids = remaining_ids_in_pairs.split(',')
        unmerged_ids = []
        confidence_scores = {}
        note = ''
        
    for res in pair_results:
        confidence_scores[res["disconnected_id"]] = res["confidence"]
        if res["same_as_remaining"]:
            merged_ids.append(res["disconnected_id"])
        else:
            unmerged_ids.append(res["disconnected_id"])

    note += generate_merge_note_if_needed(merged_ids)
    if not note:
        note = None
    else: 
        note = note.strip()

    record = {
        "resolution": "merged" if not unmerged_ids else "partial",
        "merged_entries": merged_ids,
        "unmerged_entries": unmerged_ids,
        "source": model_name,
        "confidence_scores": confidence_scores,
        "timestamp": datetime.now().isoformat(),
        "notes": note
    }

    return {block_id: record}



def build_disambiguated_record_manual(block_id, block, issue_url, model_name="auto:agreement-proxy-v"):
    merged_ids = [entry["id"] for entry in block.get("remaining", [])]
    unmerged_ids = [entry["id"] for entry in block.get("disconnected", [])]
    resolution = "manual_review_pending"
    
    record = {
        "resolution": resolution,
        "merged_entries": merged_ids,
        "unmerged_entries": unmerged_ids,
        "source": model_name,
        "confidence_scores": {},
        "timestamp": datetime.now().isoformat(),
        "notes": f"Manual review needed. Issue URL: {issue_url}"
    }

    return {block_id: record}


def build_disambiguated_record_after_human(conflict_id, conflict, decision):
    merged_ids =  [entry["id"] for entry in conflict.get("remaining", [])]
    unmerged_ids = []
    issue_url = decision.get('issue_url', None)
    
    if decision['decision'] == 'same':
        for entry in conflict["disconnected"]:
            merged_ids.append(entry["id"])

    else:
        for entry in conflict["disconnected"]:
            unmerged_ids.append(entry["id"])
        

    note = f"Decision made by human annotator in issue {issue_url}. "
    note += generate_merge_note_if_needed(merged_ids)
    if not note:
        note = None
    else: 
        note = note.strip()

    record = {
        conflict_id: {
            "resolution": decision['decision'],
            "merged_entries": merged_ids,
            "unmerged_entries": unmerged_ids,
            "source": "manual",
            "confidence_scores": {},
            "timestamp": datetime.now().isoformat(),
            "notes": note
        }
    }
    return record

    



def build_no_conflict_record(block_id, block, source="auto:no_conflict"):
    """
    Generate a disambiguated_blocks record for a block with no disconnected entries.
    This assumes all entries are already grouped (e.g., they share a repo or author).
    """

    print("BLOCK:")
    pprint(block)

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
