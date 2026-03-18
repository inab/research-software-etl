#!/usr/bin/env python3

import json
import argparse
from pathlib import Path


def json_to_jsonl(json_path: Path, jsonl_path: Path):
    with json_path.open("r", encoding="utf-8") as infile:
        data = json.load(infile)

    if not isinstance(data, dict):
        raise ValueError("Top-level JSON must be a dictionary.")

    with jsonl_path.open("w", encoding="utf-8") as outfile:
        for key, value in data.items():
            json.dump({key: value}, outfile)
            outfile.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Convert a JSON dictionary to JSONL (one key-value pair per line)."
    )
    parser.add_argument(
        "--in",
        dest="input_file",
        required=True,
        help="Input JSON file (top-level must be a dictionary)",
    )
    parser.add_argument(
        "--out",
        dest="output_file",
        required=True,
        help="Output JSONL file",
    )

    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_path = Path(args.output_file)

    json_to_jsonl(input_path, output_path)
    print(f"Converted {input_path} to {output_path}")


if __name__ == "__main__":
    main()