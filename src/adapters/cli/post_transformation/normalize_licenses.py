import argparse

from dotenv import load_dotenv

from application.services.post_transformation.normalize_tool_licenses import (
    normalize_tool_licenses,
)
from infrastructure.config import PipelineConfig
from infrastructure.db.repositories import Repositories


def update_tool_licenses(repos: Repositories):
    """
    Map tool licenses to SPDX when possible, add SPDX URLs, remove duplicates,
    and persist the normalized license list back to the database.
    """
    total = 0
    updated = 0
    unchanged = 0
    errors = 0

    for tool in repos.tools.get_all():
        total += 1

        try:
            tool_id = tool["_id"]
            current_licenses = tool.get("data", {}).get("license", [])
            normalized_licenses = normalize_tool_licenses(tool, repos.license_mapping)

            if current_licenses == normalized_licenses:
                unchanged += 1
                continue

            repos.tools.set_license(tool_id, normalized_licenses)
            updated += 1

        except Exception as e:
            errors += 1
            print(f"Error processing tool {tool.get('_id')}: {e}")

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
    repos = Repositories.from_config(config)

    update_tool_licenses(repos)


if __name__ == "__main__":
    main()
