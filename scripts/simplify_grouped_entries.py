#!/usr/bin/env python3

import json
import argparse
from pathlib import Path


def simplify_blocks(input_path: Path, output_path: Path):
    with input_path.open("r", encoding="utf-8") as f:
        blocks = json.load(f)

    for block in blocks.values():
        block["instances"] = [
            instance["_id"] for instance in block.get("instances", [])
        ]

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(blocks, f, indent=2)

    print(f"Grouped entries simplified and saved to '{output_path}'.")


def main():
    parser = argparse.ArgumentParser(
        description="Simplify grouped entries blocks by keeping only instance _id values."
    )
    parser.add_argument(
        "--in",
        dest="input_file",
        required=True,
        help="Input JSON file with grouped entries",
    )
    parser.add_argument(
        "--out",
        dest="output_file",
        required=True,
        help="Output JSON file for simplified blocks",
    )

    args = parser.parse_args()

    simplify_blocks(Path(args.input_file), Path(args.output_file))


if __name__ == "__main__":
    main()