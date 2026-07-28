"""
Build a small sampled copy of the raw ``alambiqueDev`` collection for fast test
runs of the pipeline.

The full pipeline reads ~235k raw docs from ``alambiqueDev`` and takes a long
time end to end. This script draws a per-source random sample into a separate
collection (default ``alambique_test``) so ``rsetl run`` can exercise every
stage on a few thousand docs instead. The source collection is never modified.

Connection details (MONGO_HOST/PORT/USER/PWD/...) are read from ``.env`` via the
project's MongoDBAdapter, exactly like the pipeline itself. This script lives
under scripts/ and constructs its own adapter, which is allowed there (see
CLAUDE.md: one-off scripts are outside the no-singleton rule).

Usage:
    python scripts/testing/sample_alambique.py
    python scripts/testing/sample_alambique.py --dst alambique_test

Tune the per-source caps in CAPS below to grow or shrink the test set. A source
with fewer docs than its cap contributes all it has; a source absent from the
raw data contributes nothing.
"""

from __future__ import annotations

import argparse

from infrastructure.db.mongo.mongo_adapter import MongoDBAdapter

# Per-source sample caps. Total ~4900 docs with these values.
# opeb_metrics are metrics that ATTACH to tools rather than create them, so a
# modest slice is enough to exercise that path without dominating the run.
CAPS = {
    "biotools": 1500,
    "bioconda_recipes": 600,
    "bioconda": 600,
    "github": 500,
    "bioconductor": 400,
    "galaxy_metadata": 400,
    "toolshed": 300,
    "sourceforge": 200,
    "galaxy": 200,
    "opeb_metrics": 800,
}

SOURCE_FIELD = "@data_source"


def build_sample(src_name: str, dst_name: str) -> None:
    db = MongoDBAdapter().db
    src = db[src_name]
    if src.estimated_document_count() == 0:
        raise SystemExit(
            f"Source collection {src_name!r} is empty or missing; nothing to sample."
        )

    db.drop_collection(dst_name)
    dst = db[dst_name]

    grand = 0
    for source, cap in CAPS.items():
        avail = src.count_documents({SOURCE_FIELD: source})
        if avail == 0:
            print(f"  {source:20} 0 (none available)")
            continue
        size = min(cap, avail)
        docs = list(
            src.aggregate(
                [{"$match": {SOURCE_FIELD: source}}, {"$sample": {"size": size}}],
                allowDiskUse=True,
            )
        )
        # $sample can return duplicate docs on large collections; dedupe by _id
        # so counts are exact and insert_many does not choke on a repeated _id.
        seen: set = set()
        uniq = []
        for d in docs:
            if d["_id"] not in seen:
                seen.add(d["_id"])
                uniq.append(d)
        dst.insert_many(uniq, ordered=False)
        grand += len(uniq)
        print(f"  {source:20} inserted {len(uniq):5} (cap {cap}, avail {avail})")

    print(f"TOTAL {dst_name} docs: {dst.estimated_document_count()}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--src", default="alambiqueDev", help="Source raw collection to sample from"
    )
    parser.add_argument(
        "--dst", default="alambique_test", help="Destination sample collection"
    )
    args = parser.parse_args()
    print(f"Sampling {args.src} -> {args.dst}")
    build_sample(args.src, args.dst)


if __name__ == "__main__":
    main()
