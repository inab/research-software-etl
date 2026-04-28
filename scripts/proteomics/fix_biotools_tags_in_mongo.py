#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient


DEFAULT_JSON = Path("scripts/proteomics/biotools_proteomics_tools.json")
DEFAULT_COLLECTION = "toolsDev"
CANONICAL_TAG = "Proteomics"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Synchronize the Proteomics tag in MongoDB tools with a bio.tools JSON file, "
            "matching documents through aggregated source ids like "
            "'biotools/<biotoolsID>/<type>/<version>'. "
            "Docs whose sources match the JSON list will keep/add the canonical "
            "'Proteomics' tag. Docs with 'proteomics'/'Proteomics' that do not match "
            "the JSON list will have that tag removed."
        )
    )
    parser.add_argument(
        "--json-path",
        type=Path,
        default=DEFAULT_JSON,
        help=f"Path to the bio.tools JSON file (default: {DEFAULT_JSON})",
    )
    parser.add_argument(
        "--collection",
        default=DEFAULT_COLLECTION,
        help=f"MongoDB collection name (default: {DEFAULT_COLLECTION})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without writing to MongoDB.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of bio.tools records to load.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level.",
    )
    return parser


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(levelname)s: %(message)s",
    )


def load_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list in {path}, got {type(data).__name__}")

    return data


def get_mongo_collection(collection_name: str):
    load_dotenv()

    mongo_host = os.getenv("MONGO_HOST", "localhost")
    mongo_port = int(os.getenv("MONGO_PORT", "27017"))
    mongo_user = os.getenv("MONGO_USER")
    mongo_pwd = os.getenv("MONGO_PWD")
    mongo_db = os.getenv("MONGO_DB") or os.getenv("ALAMBIQUE")
    mongo_auth_src = os.getenv("MONGO_AUTH_SRC", "admin")

    if not mongo_db:
        raise RuntimeError("Missing MONGO_DB (or ALAMBIQUE) environment variable.")

    client_kwargs: dict[str, Any] = {
        "host": mongo_host,
        "port": mongo_port,
    }

    if mongo_user and mongo_pwd:
        client_kwargs["username"] = mongo_user
        client_kwargs["password"] = mongo_pwd
        client_kwargs["authSource"] = mongo_auth_src

    client = MongoClient(**client_kwargs)
    db = client[mongo_db]
    return db[collection_name]


def normalize_tags(raw_tags: Any) -> list[str]:
    if raw_tags is None:
        return []

    if isinstance(raw_tags, str):
        value = raw_tags.strip()
        return [value] if value else []

    if isinstance(raw_tags, list):
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in raw_tags:
            if item is None:
                continue
            text = str(item).strip()
            if not text:
                continue
            if text not in seen:
                seen.add(text)
                cleaned.append(text)
        return cleaned

    text = str(raw_tags).strip()
    return [text] if text else []


def get_doc_sources(doc: dict[str, Any]) -> list[str]:
    """
    Return aggregated source ids from the top-level 'source' array.
    Fall back to 'sources' just in case some docs use that spelling.
    """
    for key in ("source", "sources"):
        raw = doc.get(key)
        if isinstance(raw, list):
            values: list[str] = []
            for item in raw:
                if item is None:
                    continue
                text = str(item).strip()
                if text:
                    values.append(text)
            return values
    return []


def build_allowed_biotools_prefixes(
    tools: list[dict[str, Any]],
) -> set[str]:
    """
    Build a set like:
        {'biotools/morpheus', 'biotools/maxquant', ...}
    """
    prefixes: set[str] = set()

    for tool in tools:
        biotools_id = tool.get("biotoolsID")
        if not biotools_id:
            logging.warning("Skipping record without biotoolsID: %s", tool.get("name"))
            continue

        prefix = f"biotools/{str(biotools_id).strip().lower()}"
        prefixes.add(prefix)

    return prefixes


def doc_matches_allowed_biotools_prefix(
    doc: dict[str, Any],
    allowed_prefixes: set[str],
) -> bool:
    """
    A doc is considered in the proteomics list if any aggregated source id starts with:
        biotools/<biotoolsID>/
    where biotools/<biotoolsID> is in the allowed set.
    """
    for source_id in get_doc_sources(doc):
        source_id_lc = source_id.lower()
        parts = source_id_lc.split("/")
        if len(parts) < 2:
            continue
        if parts[0] != "biotools":
            continue

        prefix = f"{parts[0]}/{parts[1]}"
        if prefix in allowed_prefixes:
            return True

    return False


def build_updated_tags(current_tags: list[str], should_have_proteomics: bool) -> list[str]:
    """
    Remove any case variant of 'proteomics' and then re-add the canonical
    'Proteomics' tag only if the doc should have it.
    Preserve all unrelated tags and original order as much as possible.
    """
    cleaned = [tag for tag in current_tags if tag.casefold() != "proteomics"]

    if should_have_proteomics:
        cleaned.append(CANONICAL_TAG)

    # de-duplicate while preserving order
    deduped: list[str] = []
    seen: set[str] = set()
    for tag in cleaned:
        if tag not in seen:
            seen.add(tag)
            deduped.append(tag)

    return deduped


def tags_equal_case_sensitive(a: list[str], b: list[str]) -> bool:
    return a == b


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    setup_logging(args.log_level)

    tools = load_json(args.json_path)
    if args.limit is not None:
        tools = tools[: args.limit]

    allowed_prefixes = build_allowed_biotools_prefixes(tools)
    logging.info("Loaded %d allowed biotools prefixes from JSON.", len(allowed_prefixes))

    collection = get_mongo_collection(args.collection)

    # We only need to inspect:
    # 1) docs currently tagged as proteomics/proteomics
    # 2) docs that contain some biotools aggregated source, because they might need the tag added
    #
    # To keep it simple and correct, fetch the union by scanning docs that either:
    # - already have a proteomics tag, OR
    # - have at least one aggregated biotools/... source
    #
    # Since source is an array of strings, this regex works on array elements too.
    candidate_query = {
        "$or": [
            {"data.tags": {"$regex": r"^proteomics$", "$options": "i"}},
            {"source": {"$regex": r"^biotools/"}},
            {"sources": {"$regex": r"^biotools/"}},
        ]
    }

    inspected = 0
    updated = 0
    unchanged = 0
    should_have_count = 0
    should_not_have_count = 0
    currently_tagged_count = 0

    cursor = collection.find(candidate_query)

    for doc in cursor:
        inspected += 1

        current_tags = normalize_tags(doc.get("data", {}).get("tags"))
        has_proteomics_now = any(tag.casefold() == "proteomics" for tag in current_tags)
        if has_proteomics_now:
            currently_tagged_count += 1

        should_have_proteomics = doc_matches_allowed_biotools_prefix(doc, allowed_prefixes)
        if should_have_proteomics:
            should_have_count += 1
        else:
            should_not_have_count += 1

        new_tags = build_updated_tags(current_tags, should_have_proteomics)

        if tags_equal_case_sensitive(current_tags, new_tags):
            unchanged += 1
            logging.debug(
                "Unchanged _id=%s | should_have=%s | tags=%s",
                doc["_id"],
                should_have_proteomics,
                current_tags,
            )
            continue

        logging.info(
            "Updating _id=%s | should_have=%s | tags %s -> %s",
            doc["_id"],
            should_have_proteomics,
            current_tags,
            new_tags,
        )

        if not args.dry_run:
            result = collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"data.tags": new_tags}},
            )
            if result.modified_count == 1:
                updated += 1
            else:
                logging.warning("No modification reported for _id=%s", doc["_id"])
        else:
            updated += 1

    logging.info("---- Summary ----")
    logging.info("Candidate docs inspected: %d", inspected)
    logging.info("Docs currently tagged proteomics: %d", currently_tagged_count)
    logging.info("Docs that should have Proteomics: %d", should_have_count)
    logging.info("Docs that should NOT have Proteomics: %d", should_not_have_count)
    logging.info("Docs updated: %d", updated)
    logging.info("Docs unchanged: %d", unchanged)
    logging.info("Mode: %s", "dry-run" if args.dry_run else "write")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())