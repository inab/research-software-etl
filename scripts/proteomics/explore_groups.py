import json
from pathlib import Path
from collections import Counter

from bson import ObjectId
from infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


GROUPED_FILE = Path(
    "data/integration/runs/20260408T093144Z-84587146-test-grouping-2/"
    "grouped_entries.simplified.20260408T093144Z-84587146-test-grouping-2.jsonl"
)

PRETOOLS_COLLECTION = "pretoolsDev"
OUTPUT_JSON = Path("missing_pretools_from_grouped_entries.json")
OUTPUT_JSONL = Path("missing_pretools_from_grouped_entries.jsonl")


def load_grouped_instance_ids(path: Path) -> set[str]:
    grouped_ids = set()

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            record = json.loads(line)
            if len(record) != 1:
                raise ValueError(
                    f"Line {line_no}: expected one top-level block key, got {len(record)}"
                )

            _, block_data = next(iter(record.items()))
            instances = block_data.get("instances", [])

            for inst in instances:
                if inst is not None:
                    grouped_ids.add(str(inst))

    return grouped_ids


def get_collection():
    return mongo_adapter.get_collection(PRETOOLS_COLLECTION)


def summarize_missing(missing_docs: list[dict]) -> None:
    print("\nSummary of missing records")
    print("-" * 40)
    print(f"Total missing pretools: {len(missing_docs)}")

    source_counter = Counter()
    type_counter = Counter()

    for doc in missing_docs:
        data = doc.get("data", {})
        source = data.get("source") or doc.get("source") or "UNKNOWN"
        tool_type = data.get("type") or doc.get("type") or "UNKNOWN"

        if isinstance(source, list):
            for s in source:
                source_counter[str(s)] += 1
        else:
            source_counter[str(source)] += 1

        if isinstance(tool_type, list):
            for t in tool_type:
                type_counter[str(t)] += 1
        else:
            type_counter[str(tool_type)] += 1

    print("\nMissing by source:")
    for source, count in source_counter.most_common():
        print(f"  {source}: {count}")

    print("\nMissing by type:")
    for tool_type, count in type_counter.most_common():
        print(f"  {tool_type}: {count}")


def make_output_doc(doc: dict) -> dict:
    data = doc.get("data", {})

    out = {
        "_id": str(doc["_id"]),
        "name": data.get("name"),
        "type": data.get("type"),
        "version": data.get("version"),
        "source": data.get("source"),
        "links": data.get("links"),
    }
    return out


def main():
    grouped_ids = load_grouped_instance_ids(GROUPED_FILE)
    print(f"Grouped instance IDs loaded: {len(grouped_ids)}")

    collection = get_collection()
    cursor = collection.find({})

    missing_docs = []
    total = 0

    for doc in cursor:
        total += 1
        doc_id = str(doc["_id"])

        if doc_id not in grouped_ids:
            missing_docs.append(doc)

    print(f"Total pretools checked: {total}")
    print(f"Missing from grouped entries: {len(missing_docs)}")

    summarize_missing(missing_docs)

    output_docs = [make_output_doc(doc) for doc in missing_docs]

    with OUTPUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(output_docs, f, indent=2, ensure_ascii=False)

    with OUTPUT_JSONL.open("w", encoding="utf-8") as f:
        for record in output_docs:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\nSaved JSON output to: {OUTPUT_JSON}")
    print(f"Saved JSONL output to: {OUTPUT_JSONL}")

    if missing_docs:
        print("\nFirst 10 missing IDs:")
        for doc in missing_docs[:10]:
            print(str(doc["_id"]))


if __name__ == "__main__":
    main()