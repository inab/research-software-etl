import json


# ----------------------------------------------------
# Count blocks and pairwise decisions from final disambiguation file
# ----------------------------------------------------

db_final_path = (
    "data/integration/runs/"
    "20260421T111602Z-8d84134d-manual_group_correction/"
    "disambiguation.20260421T111602Z-8d84134d-manual_group_correction.jsonl"
)


def load_disambiguation_blocks(path: str) -> dict[str, dict]:
    """
    Load disambiguation blocks from JSONL.

    Expected line format:
    {"block_id": {...block_data...}}

    Returns:
        dict[str, dict]: {block_id: block_data}
    """
    blocks = {}

    with open(path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                print(f"Error decoding JSON in {path}, line {line_number}: {line}")
                continue

            if not isinstance(record, dict):
                print(
                    f"Unexpected record type in {path}, line {line_number}: "
                    f"expected dict, got {type(record).__name__}"
                )
                continue

            if len(record) != 1:
                print(
                    f"Unexpected record structure in {path}, line {line_number}: "
                    f"expected a single-key dict, got keys {list(record.keys())}"
                )
                continue

            block_id, block_data = next(iter(record.items()))

            if block_id in blocks:
                print(f"Duplicate block ID found in {path}: {block_id}")

            blocks[block_id] = block_data

    return blocks


db_final = load_disambiguation_blocks(db_final_path)

# Block-level counts
non_conflictive = 0
conflictive = 0
manual_review_pending = 0
blocks_with_unclear = 0

# Pairwise counts
total_pairwise_comparisons = 0
pairwise_solved_by_llm = 0
pairwise_solved_by_human = 0
pairwise_human_unclear = 0
pairwise_unknown = 0
pairwise_other_sources = {}

for key, block in db_final.items():
    if "_secondary_" in key:
        # Secondary blocks are not counted as independent blocks
        continue

    resolution = block.get("resolution")

    # -------------------------
    # Block-level classification
    # -------------------------
    if resolution == "no_conflict":
        non_conflictive += 1
    else:
        conflictive += 1

        if resolution == "manual_review_pending":
            manual_review_pending += 1

        # count blocks that contain at least one unclear comparison
        unclear_entries = block.get("unclear_entries", [])
        pairwise_summary = block.get("pairwise_summary", {})
        if unclear_entries or pairwise_summary.get("human_unclear", 0) > 0:
            blocks_with_unclear += 1

    # -------------------------
    # Pairwise summary
    # -------------------------
    pairwise_summary = block.get("pairwise_summary", {})

    total_pairwise_comparisons += pairwise_summary.get("total_pairs", 0)
    pairwise_solved_by_llm += pairwise_summary.get("llm", 0)
    pairwise_solved_by_human += pairwise_summary.get("human", 0)
    pairwise_human_unclear += pairwise_summary.get("human_unclear", 0)
    pairwise_unknown += pairwise_summary.get("unknown", 0)

    other_sources = pairwise_summary.get("other_sources", {})
    if isinstance(other_sources, dict):
        for source_name, count in other_sources.items():
            pairwise_other_sources[source_name] = (
                pairwise_other_sources.get(source_name, 0) + count
            )
    elif other_sources:
        print(
            f"WARNING: Block {key} has malformed 'other_sources': "
            f"{type(other_sources).__name__}"
        )

    # Optional warning if a conflictive block has no pairwise summary at all
    if resolution != "no_conflict" and not pairwise_summary:
        print(
            f"WARNING: Conflictive block {key} has no 'pairwise_summary' field."
        )


print(f"Total number of blocks: {non_conflictive + conflictive}")
print(f"-- Number of non-conflictive blocks: {non_conflictive}")
print(f"-- Number of conflictive blocks: {conflictive}")
print(f"    -- Number of blocks still manual_review_pending: {manual_review_pending}")
print(f"    -- Number of blocks with at least one unclear pair: {blocks_with_unclear}")

print()
print(f"Total number of pairwise comparisons: {total_pairwise_comparisons}")
print(f"-- Number of pairwise decisions solved by LLM: {pairwise_solved_by_llm}")
print(f"-- Number of pairwise decisions solved by human: {pairwise_solved_by_human}")
print(f"-- Number of pairwise decisions marked unclear by human: {pairwise_human_unclear}")
print(f"-- Number of pairwise decisions with unknown source: {pairwise_unknown}")

if pairwise_other_sources:
    print("-- Other pairwise sources:")
    for source_name, count in sorted(pairwise_other_sources.items()):
        print(f"   -- {source_name}: {count}")