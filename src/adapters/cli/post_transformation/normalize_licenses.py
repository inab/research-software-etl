import argparse

from dotenv import load_dotenv

from application.services.post_transformation.normalize_tool_licenses import (
    normalize_tool_licenses,
)
from infrastructure.config import PipelineConfig
from infrastructure.db.repositories import Repositories, from_config


def update_tool_licenses(repos: Repositories, write_batch_size: int = 1000):
    """
    Map tool licenses to SPDX when possible, add SPDX URLs, remove duplicates,
    and persist the normalized license list back to the database.

    Reads only each tool's ``_id`` and ``data.license`` (a projected stream, not
    the whole ~50k documents) in large cursor batches, and flushes the changed
    licenses via ``bulk_set_licenses`` -- one round-trip per batch instead of one
    per tool. The large ``read_batch_size`` matters: at the driver default (~100)
    a 50k scan spends most of its time in ``getMore`` round-trips.
    """
    read_batch_size = 5000
    total = 0
    updated = 0
    unchanged = 0
    errors = 0

    pending: dict = {}

    def flush():
        if pending:
            repos.tools.bulk_set_licenses(pending)
            pending.clear()

    projection = {"_id": 1, "data.license": 1}
    for tool in repos.tools.iter_projected({}, projection, batch_size=read_batch_size):
        total += 1

        try:
            tool_id = tool["_id"]
            current_licenses = tool.get("data", {}).get("license", [])
            normalized_licenses = normalize_tool_licenses(tool, repos.license_mapping)

            if current_licenses == normalized_licenses:
                unchanged += 1
                continue

            pending[tool_id] = normalized_licenses
            updated += 1

            if len(pending) >= write_batch_size:
                flush()

        except Exception as e:
            errors += 1
            print(f"Error processing tool {tool.get('_id')}: {e}")

    flush()

    print(f"Total tools processed: {total}")
    print(f"Updated docs: {updated}")
    print(f"Unchanged docs: {unchanged}")
    print(f"Errors: {errors}")

    return {
        "total": total,
        "updated": updated,
        "unchanged": unchanged,
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Normalize the license field of every tool against SPDX."
    )
    parser.add_argument(
        "--env-file",
        "-e",
        help="File containing environment variables to be set before running",
        default=".env",
    )
    args = parser.parse_args()

    load_dotenv(args.env_file)

    config = PipelineConfig.from_env()
    repos = from_config(config)

    update_tool_licenses(repos)


if __name__ == "__main__":
    main()
