import datetime

def build_disambiguated_record(block_id, block, pair_results, model_name="auto:agreement-proxy-v"):
    """
    Given the results of pairwise disambiguation, build a complete
    record for disambiguated_blocks.json.
    """
    merged_ids = [entry["id"] for entry in block.get("remaining", [])]
    unmerged_ids = []
    confidence_scores = {}

    for res in pair_results:
        confidence_scores[res["disconnected_id"]] = res["confidence"]
        if res["same_as_remaining"]:
            merged_ids.append(res["disconnected_id"])
        else:
            unmerged_ids.append(res["disconnected_id"])

    record = {
        "resolution": "merged" if not unmerged_ids else "partial",
        "merged_entries": merged_ids,
        "unmerged_entries": unmerged_ids,
        "source": model_name,
        "confidence_scores": confidence_scores,
        "timestamp": datetime.utcnow().isoformat(),
        "notes": None
    }

    return {block_id: record}



def build_no_conflict_record(block_id, block, source="auto:no_disagreement"):
    """
    Generate a disambiguated_blocks record for a block with no disconnected entries.
    This assumes all entries are already grouped (e.g., they share a repo or author).
    """
    merged_ids = [entry["id"] for entry in block.get("instances", [])]

    return {
        block_id: {
            "resolution": "no_conflict",
            "merged_entries": merged_ids,
            "unmerged_entries": [],
            "source": source,
            "confidence_scores": {},
            "timestamp": datetime.utcnow().isoformat(),
            "notes": "All entries grouped heuristically or by shared metadata. No disambiguation needed."
        }
    }
