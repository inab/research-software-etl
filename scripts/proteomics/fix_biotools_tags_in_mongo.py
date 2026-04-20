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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Make MongoDB tool tags match the tags from a bio.tools JSON file, "
            "matching tools by entries in the 'source' field like "
            "'biotools/<biotoolsID>/...'."
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
        help="Optional limit on number of bio.tools records to process.",
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
        cleaned = []
        seen = set()
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

    return [str(raw_tags).strip()] if str(raw_tags).strip() else []


def sorted_for_compare(values: list[str]) -> list[str]:
    return sorted(values, key=lambda x: x.casefold())


def source_regex_for_biotools_id(biotools_id: str) -> re.Pattern[str]:
    escaped = re.escape(biotools_id)
    return re.compile(rf"^biotools/{escaped}/")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    setup_logging(args.log_level)

    tools = load_json(args.json_path)
    if args.limit is not None:
        tools = tools[: args.limit]

    collection = get_mongo_collection(args.collection)

    processed = 0
    found_tools = 0
    updated_docs = 0
    unchanged_docs = 0
    missing_tools = 0
    matched_docs_total = 0

    for tool in tools:
        processed += 1

        biotools_id = tool.get("biotoolsID")
        if not biotools_id:
            logging.warning("Skipping record without biotoolsID: %s", tool.get("name"))
            continue

        desired_tags = normalize_tags(tool.get("collectionID"))
        regex = source_regex_for_biotools_id(biotools_id.lower())

        matches = list(collection.find({"source": {"$regex": regex}}))
        if not matches:
            missing_tools += 1
            logging.info("Not found in Mongo: biotools/%s", biotools_id)
            continue

        found_tools += 1
        matched_docs_total += len(matches)

        if len(matches) > 1:
            logging.warning(
                "Multiple Mongo docs matched biotools/%s (%d docs)",
                biotools_id,
                len(matches),
            )

        for doc in matches:
            current_tags = normalize_tags(doc.get("data", {}).get("tags"))

            if sorted_for_compare(current_tags) == sorted_for_compare(desired_tags):
                unchanged_docs += 1
                logging.debug(
                    "Already up to date for _id=%s | biotools/%s",
                    doc["_id"],
                    biotools_id,
                )
                continue

            logging.info(
                "Updating _id=%s | biotools/%s | tags %s -> %s",
                doc["_id"],
                biotools_id,
                current_tags,
                desired_tags,
            )

            if not args.dry_run:
                result = collection.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"data.tags": desired_tags}},
                )
                if result.modified_count == 1:
                    updated_docs += 1
                else:
                    logging.warning(
                        "No modification reported for _id=%s", doc["_id"]
                    )
            else:
                updated_docs += 1

    logging.info("---- Summary ----")
    logging.info("Processed bio.tools records: %d", processed)
    logging.info("bio.tools records found in Mongo: %d", found_tools)
    logging.info("Mongo docs matched in total: %d", matched_docs_total)
    logging.info("Mongo docs updated: %d", updated_docs)
    logging.info("Mongo docs already matching: %d", unchanged_docs)
    logging.info("bio.tools records not found in Mongo: %d", missing_tools)
    logging.info("Mode: %s", "dry-run" if args.dry_run else "write")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())