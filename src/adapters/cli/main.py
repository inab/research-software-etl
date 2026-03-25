from __future__ import annotations

import argparse
import sys
from pathlib import Path

from adapters.cli import check_environment
from adapters.cli import web_availability
from adapters.cli.pipeline_full import run_full, STAGES
from adapters.cli.run_transformation import run_transformation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rsetl",
        description=(
            "Research Software Observatory – Data Pipeline.\n"
            "Run ETL, integration, and enrichment stages for software metadata."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_p = subparsers.add_parser("run", help="Run the integration pipeline")
    run_p.add_argument("--tag", dest="run_tag", help="Optional tag appended to run ID")
    run_p.add_argument(
        "--resume-run",
        help="Resume an existing run by run ID or run directory path",
    )
    run_p.add_argument(
        "--no-merge",
        dest="do_merge_to_db",
        action="store_false",
        help="Skip merge stage",
    )
    run_p.add_argument(
        "--no-human-updates",
        dest="human_updates",
        action="store_false",
        help="Skip human update stage",
    )
    run_p.add_argument(
        "--remove-opeb-metrics",
        dest="remove_opeb_metrics",
        action="store_false",
        help="Enable removal of OEB metrics stage",
    )
    run_p.set_defaults(remove_opeb_metrics=True)
    run_p.add_argument(
        "--from-stage",
        choices=STAGES,
        help="Start pipeline from this stage",
    )
    run_p.add_argument(
        "--until",
        dest="until_stage",
        choices=STAGES,
        help="Run pipeline until this stage (inclusive)",
    )
    run_p.add_argument(
        "--only",
        dest="only_stage",
        choices=STAGES,
        help="Run only one stage",
    )
    run_p.add_argument("--python-exe", default="python", help="Python executable for subprocesses")
    run_p.add_argument("--workdir", default=".", help="Working directory (default: current)")
    run_p.add_argument("--runs-root", default="data/integration/runs", help="Root folder for run outputs")

    tr_p = subparsers.add_parser(
        "run-transformation",
        help="Run only the transformation step",
    )
    tr_p.add_argument("--tag", dest="run_tag", help="Optional tag appended to run ID")
    tr_p.add_argument("--sources", default="all", help="Sources passed to the transformation step")
    tr_p.add_argument("--python-exe", default="python", help="Python executable for subprocesses")
    tr_p.add_argument("--workdir", default=".", help="Working directory (default: current)")
    tr_p.add_argument("--runs-root", default="data/integration/runs", help="Root folder for run outputs")

    subparsers.add_parser("check-env", help="Check environment variables and API connectivity")

    wa_p = subparsers.add_parser(
        "run-webavailability",
        help="Run daily web availability update (and ensure ToolsDev URLs exist)",
    )
    wa_p.add_argument(
        "wa_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed to the web availability job",
    )

    args = parser.parse_args(argv)

    if args.command == "check-env":
        check_environment.main()
        return 0

    if args.command == "run":
        run_full(
            workdir=Path(args.workdir),
            runs_root=args.runs_root,
            run_tag=args.run_tag,
            remove_opeb_metrics=args.remove_opeb_metrics,
            human_updates=args.human_updates,
            do_merge_to_db=args.do_merge_to_db,
            python_exe=args.python_exe,
            from_stage=args.from_stage,
            until_stage=args.until_stage,
            only_stage=args.only_stage,
            resume_run=args.resume_run,
        )
        return 0

    if args.command == "run-transformation":
        run_transformation(
            workdir=Path(args.workdir),
            runs_root=args.runs_root,
            run_tag=args.run_tag,
            sources=args.sources,
            python_exe=args.python_exe,
        )
        return 0

    if args.command == "run-webavailability":
        return web_availability.main(args.wa_args)

    return 0


if __name__ == "__main__":
    sys.exit(main())