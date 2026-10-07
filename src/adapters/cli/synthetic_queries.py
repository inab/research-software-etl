"""
Command-line interface for synthetic search queries (semantic search).

    rsetl synthetic-queries export    # prompts for tools that need queries -> JSONL
    rsetl synthetic-queries import    # MN5 batch completions (JSONL) -> semantic_search
    rsetl synthetic-queries generate  # online: one Gepeto call per tool

`export` / `import` bracket the offline batch job on MareNostrum 5 (see
hpc/mn5/README.md). `generate` does the same work online through Gepeto.
All three are incremental; see application/use_cases/semantic_search.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Iterator

from dotenv import load_dotenv

from application.use_cases.semantic_search.synthetic_queries import (
    export_query_requests,
    generate_synthetic_queries,
    import_query_results,
)
from infrastructure.config import Credentials, PipelineConfig
from infrastructure.db.repositories import from_config
from infrastructure.external.gepeto import GepetoClient
from infrastructure.logging_config import resolve_level


def _read_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                logging.warning(f"Skipping unparseable line {number} of {path}: {exc}")


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--env-file", "-e", default=".env")
    common.add_argument(
        "--loglevel", "-l", default=os.getenv("LOG_LEVEL", "INFO"), help="Log level."
    )

    scope = argparse.ArgumentParser(add_help=False)
    scope.add_argument(
        "--collections",
        "-c",
        default="tools",
        help="'tools' for every tool, or a tag to process only tools with that data.tags.",
    )
    scope.add_argument(
        "--limit", type=int, default=None, help="At most N tools needing an LLM call."
    )
    scope.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even tools whose stored queries are current (e.g. after "
        "switching models).",
    )

    parser = argparse.ArgumentParser(
        prog="rsetl synthetic-queries",
        description="Generate synthetic search queries for tools (semantic search).",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    exp = sub.add_parser(
        "export",
        parents=[common, scope],
        help="Write prompts for tools that need queries to JSONL (for the MN5 job).",
    )
    exp.add_argument(
        "--output",
        "-o",
        default=None,
        help="Requests file (default: config synthetic_query_requests_path).",
    )

    imp = sub.add_parser(
        "import",
        parents=[common],
        help="Store the MN5 job's completions in the semantic_search collection.",
    )
    imp.add_argument(
        "--input",
        "-i",
        nargs="+",
        default=None,
        help="Results file(s), e.g. the MN5 shard parts "
        "(default: config synthetic_query_results_path).",
    )

    gen = sub.add_parser(
        "generate",
        parents=[common, scope],
        help="Generate queries online through Gepeto.",
    )
    gen.add_argument(
        "--model", default=None, help="Gepeto model (default: GEPETO_QUERY_MODEL)."
    )
    gen.add_argument("--workers", type=int, default=4, help="Concurrent LLM calls.")
    gen.add_argument("--temperature", type=float, default=0.5)
    gen.add_argument(
        "--dry-run", action="store_true", help="Print queries; write nothing."
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_dotenv(args.env_file, override=True)
    logging.basicConfig(level=resolve_level(args.loglevel))

    config = PipelineConfig.from_env(
        synthetic_query_requests_path=getattr(args, "output", None)
    )
    repos = from_config(config)

    if args.action == "export":
        requests, summary = export_query_requests(
            repos, tag=args.collections, limit=args.limit, force=args.force
        )
        path = config.synthetic_query_requests_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for request in requests:
                handle.write(json.dumps(request, ensure_ascii=False) + "\n")
        print(f"Wrote {len(requests)} requests to {path}")

    elif args.action == "import":
        paths = (
            [Path(p) for p in args.input]
            if args.input
            else [config.synthetic_query_results_path]
        )
        missing = [str(p) for p in paths if not p.exists()]
        if missing:
            print(f"[ERROR] Results file(s) not found: {missing}", file=sys.stderr)
            return 1
        summary = import_query_results(
            repos, (row for path in paths for row in _read_jsonl(path))
        )

    else:
        credentials = Credentials.from_env().require("gepeto_api_key")
        summary = generate_synthetic_queries(
            repos,
            GepetoClient(credentials.gepeto_api_key),
            args.model or config.gepeto_query_model,
            tag=args.collections,
            limit=args.limit,
            force=args.force,
            workers=args.workers,
            temperature=args.temperature,
            dry_run=args.dry_run,
        )

    print(f"Done. {summary.line()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
