import json


# ----------------------------------------------------
# Count blocks from the final disambiguation file
# ----------------------------------------------------

db_final_path = "data/integration/runs/20260327T114032Z-c227780a-pre-annotation/disambiguation.20260327T114032Z-c227780a-pre-annotation.jsonl"


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

non_conflictive = 0
conflictive = 0
solved_by_llms = 0
solved_by_human = 0
unclear = 0

for key, block in db_final.items():
    if "_secondary_" in key:
        # Secondary blocks are not counted as independent blocks
        continue

    resolution = block.get("resolution")
    source = block.get("source", "")

    if resolution == "no_conflict":
        non_conflictive += 1
        continue

    conflictive += 1

    if resolution == "unclear":
        unclear += 1

    elif source == "manual":
        solved_by_human += 1

    elif source.startswith("auto:agreement-proxy-v"):
        solved_by_llms += 1

    else:
        print(
            f"WARNING: Block {key} has conflictive resolution '{resolution}' "
            f"but unknown source '{source}'."
        )


print(f"Total number of blocks: {non_conflictive + conflictive}")
print(f"-- Number of non-conflictive blocks: {non_conflictive}")
print(f"-- Number of conflictive blocks: {conflictive}")
print(f"    -- Number of blocks solved by LLMs: {solved_by_llms}")
print(f"    -- Number of blocks solved by human: {solved_by_human}")
print(f"    -- Number of blocks still unclear: {unclear}")