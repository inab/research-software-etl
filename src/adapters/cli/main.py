"""
Main CLI entry point for the Research Software Observatory – Data Pipeline.

Usage examples:
    rsetl run                   # run the full pipeline
    rsetl run --tag test1       # run with custom tag
    rsetl run --no-merge        # skip database merge
    rsetl check-env             # check environment and API connectivity
    rsetl --help                # show usage
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from src.adapters.cli import check_environment
from src.adapters.cli.pipeline_full import run_full  


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="rsetl",
        description=(
            "Research Software Observatory – Data Pipeline.\n"
            "Run ETL, integration, and enrichment stages for software metadata."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- run subcommand ---------------------------------------------------------
    run_p = subparsers.add_parser("run", help="Run the full integration pipeline")
    run_p.add_argument("--tag", dest="run_tag", help="Optional tag appended to run ID")
    run_p.add_argument("--no-merge", dest="do_merge_to_db", action="store_false", help="Skip final merge to database")
    run_p.add_argument("--no-human-updates", dest="human_updates", action="store_false", help="Skip human update step")
    run_p.add_argument("--remove-opeb-metrics", dest="remove_opeb_metrics", action="store_true", help="Remove OEB metrics step")
    run_p.add_argument("--python-exe", default="python", help="Python executable for subprocesses")
    run_p.add_argument("--workdir", default=".", help="Working directory (default: current)")
    run_p.add_argument("--runs-root", default="data/integration/runs", help="Root folder for run outputs")

    # --- check-env subcommand ---------------------------------------------------
    subparsers.add_parser("check-env", help="Check environment variables and API connectivity")

    # --- parse -----------------------------------------------------------------
    args = parser.parse_args(argv)

    if args.command == "check-env":
        check_environment.main()
        return

    if args.command == "run":
        run_full(
            workdir=Path(args.workdir),
            runs_root=args.runs_root,
            run_tag=args.run_tag,
            remove_opeb_metrics=args.remove_opeb_metrics,
            human_updates=args.human_updates,
            do_merge_to_db=args.do_merge_to_db,
            python_exe=args.python_exe,
        )
        return
    
    ## Add `rsetl integrate-human`
    ## Add `rsetl run-publications`
    ## Add `rsetl run-webavailability`


if __name__ == "__main__":
    sys.exit(main())