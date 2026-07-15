from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from adapters.cli import enrich_publications
from adapters.cli import check_environment
from adapters.cli import web_availability
from adapters.cli.pipeline_full import PipelineError, STAGES, run_full
from adapters.cli.pipeline_runs import get_latest_run, list_runs, show_run
from adapters.cli.run_transformation import run_transformation


def _truncate(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "…"


def _print_runs_table(runs: list[dict]) -> None:
    if not runs:
        print("No runs found.")
        return

    headers = [
        "run_id",
        "updated",
        "manifest",
        "disambig",
        "resumable",
        "execs",
        "latest stages",
    ]

    rows = []
    for r in runs:
        stage_text = ", ".join(r.get("latest_executed_stages", [])) or "-"
        rows.append([
            r.get("run_id", ""),
            r.get("last_updated_utc") or r.get("created_utc") or "-",
            "yes" if r.get("has_manifest") else "no",
            "yes" if r.get("disambiguation_exists") else "no",
            "yes" if r.get("resumable") else "no",
            str(r.get("execution_count", 0)),
            _truncate(stage_text, 50),
        ])

    widths = [
        max(len(str(row[i])) for row in ([headers] + rows))
        for i in range(len(headers))
    ]

    def fmt(row: list[str]) -> str:
        return "  ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row))

    print(fmt(headers))
    print(fmt(["-" * w for w in widths]))
    for row in rows:
        print(fmt(row))


def _print_run_summary(data: dict) -> None:
    print(f"Run ID:        {data.get('run_id', '-')}")
    print(f"Run dir:       {data.get('run_dir', '-')}")
    print(f"Created:       {data.get('created_utc', '-')}")
    print(f"Last updated:  {data.get('last_updated_utc', '-')}")
    print()

    latest_execution = data.get("latest_execution", {})
    execution_history = data.get("execution_history", [])

    if latest_execution:
        stage_selection = latest_execution.get("stage_selection", {})
        print("Latest execution:")
        print(f"  Is resume:        {latest_execution.get('is_resume', False)}")
        print(f"  Resume source:    {latest_execution.get('resume_run') or '-'}")
        print(f"  Selected stages:  {', '.join(stage_selection.get('selected_stages', [])) or '-'}")
        print(f"  Executed stages:  {', '.join(stage_selection.get('executed_stages', [])) or '-'}")
        print(f"  Started:          {latest_execution.get('utc_started', '-')}")
        print(f"  Finished:         {latest_execution.get('utc_finished', '-')}")
        print()
    else:
        print("Latest execution: none")
        print()

    print(f"Execution history count: {len(execution_history)}")
    print()

    print("Paths:")
    for key, value in data.get("paths", {}).items():
        exists = "yes" if Path(value).exists() else "no"
        print(f"  {key}:")
        print(f"    path:   {value}")
        print(f"    exists: {exists}")
    print()

    latest_options = data.get("latest_options", {})
    if latest_options:
        print("Latest options:")
        for key, value in latest_options.items():
            print(f"  {key}: {value}")
        print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="rsetl",
        description=(
            "Research Software Observatory – Data Pipeline.\n"
            "Run ETL, integration, and enrichment stages for software metadata."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- run --------------------------------------------------------------------
    run_p = subparsers.add_parser("run", help="Run the integration pipeline")
    run_p.add_argument("--tag", dest="run_tag", help="Optional tag appended to run ID")
    run_p.add_argument("--resume-run", help="Resume an existing run by run ID or run directory path")
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
    run_p.add_argument("--from-stage", choices=STAGES, help="Start pipeline from this stage")
    run_p.add_argument("--until", dest="until_stage", choices=STAGES, help="Run pipeline until this stage (inclusive)")
    run_p.add_argument("--only", dest="only_stage", choices=STAGES, help="Run only one stage")
    run_p.add_argument("--python-exe", default="python", help="Python executable for subprocesses")
    run_p.add_argument("--workdir", default=".", help="Working directory (default: current)")
    run_p.add_argument("--runs-root", default="data/integration/runs", help="Root folder for run outputs")
    run_p.add_argument(
        "--dry-run-disambiguation",
        dest="dry_run_disambiguation",
        action="store_true",
        help="Run the disambiguation stage without creating conflict files or GitHub issues.",
    )
    
    # --- run-transformation -----------------------------------------------------
    tr_p = subparsers.add_parser("run-transformation", help="Run only the transformation step")
    tr_p.add_argument("--tag", dest="run_tag", help="Optional tag appended to run ID")
    tr_p.add_argument("--sources", default="all", help="Sources passed to the transformation step")
    tr_p.add_argument("--python-exe", default="python", help="Python executable for subprocesses")
    tr_p.add_argument("--workdir", default=".", help="Working directory (default: current)")
    tr_p.add_argument("--runs-root", default="data/integration/runs", help="Root folder for run outputs")
    
    # --- check-env --------------------------------------------------------------
    subparsers.add_parser("check-env", help="Check environment variables and API connectivity")

    # --- run-webavailability ----------------------------------------------------
    wa_p = subparsers.add_parser(
        "run-webavailability",
        help="Run daily web availability update (and ensure toolsDev URLs exist)",
    )
    wa_p.add_argument(
        "wa_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed to the web availability job",
    )

    # --- enrich-publications ----------------------------------------------------
    ep_p = subparsers.add_parser(
        "enrich-publications",
        help="Enrich publication metadata and citation counts using Europe PMC",
    )
    ep_p.add_argument(
        "ep_args",
        nargs=argparse.REMAINDER,
        help="Arguments passed to the enrich publications job",
    )

    # --- rollback ---------------------------------------------------------------
    rollback_p = subparsers.add_parser(
        "rollback",
        help="Restore the tools collection archived by a run, undoing its promotion",
    )
    rollback_p.add_argument("run_id", help="Run ID whose archive should be restored")
    rollback_p.add_argument(
        "--env-file", default=".env", help="File containing environment variables"
    )
    rollback_p.add_argument(
        "--yes",
        action="store_true",
        help="Do not ask for confirmation. The current tools collection is dropped.",
    )

    # --- runs -------------------------------------------------------------------
    runs_p = subparsers.add_parser("runs", help="Inspect pipeline runs")
    runs_sub = runs_p.add_subparsers(dest="runs_command", required=True)

    runs_list_p = runs_sub.add_parser("list", help="List available runs")
    runs_list_p.add_argument("--workdir", default=".", help="Working directory (default: current)")
    runs_list_p.add_argument("--runs-root", default="data/integration/runs", help="Root folder for run outputs")
    runs_list_p.add_argument("--json", action="store_true", help="Output as JSON")

    runs_show_p = runs_sub.add_parser("show", help="Show details for one run")
    runs_show_p.add_argument("run_ref", help="Run ID or full run directory path")
    runs_show_p.add_argument("--workdir", default=".", help="Working directory (default: current)")
    runs_show_p.add_argument("--runs-root", default="data/integration/runs", help="Root folder for run outputs")
    runs_show_p.add_argument("--json", action="store_true", help="Output as JSON")

    runs_latest_p = runs_sub.add_parser("latest", help="Show the latest run")
    runs_latest_p.add_argument("--workdir", default=".", help="Working directory (default: current)")
    runs_latest_p.add_argument("--runs-root", default="data/integration/runs", help="Root folder for run outputs")
    runs_latest_p.add_argument("--json", action="store_true", help="Output as JSON")

    # --- scheduler --------------------------------------------------------------
    scheduler_p = subparsers.add_parser("scheduler", help="Run scheduled pipeline jobs")
    scheduler_p.add_argument(
        "--env-file", default=".env", help="File containing environment variables"
    )
    scheduler_sub = scheduler_p.add_subparsers(dest="scheduler_command", required=True)
    scheduler_sub.add_parser("start", help="Start the scheduler in the foreground")
    scheduler_run_now_p = scheduler_sub.add_parser(
        "run-now", help="Trigger one job immediately"
    )
    scheduler_run_now_p.add_argument(
        "job",
        choices=["full_pipeline", "publication_enrichment"],
        help="Job to run once",
    )

    args = parser.parse_args(argv)

    try:
        if args.command == "check-env":
            check_environment.main()
            return 0

        if args.command == "run":
            if args.resume_run and args.run_tag:
                raise PipelineError("--tag cannot be used together with --resume-run")

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
                dry_run_disambiguation=args.dry_run_disambiguation
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
        
        if args.command == "enrich-publications":
            return enrich_publications.main(args.ep_args)

        if args.command == "rollback":
            from dotenv import load_dotenv

            from application.use_cases.integration.finalize_run import (
                archive_name,
                rollback_run,
            )
            from infrastructure.config import PipelineConfig
            from infrastructure.db.repositories import from_config

            load_dotenv(args.env_file)
            config = PipelineConfig.from_env()
            repos = from_config(config)

            # Rolling back drops the live collection. Say so before doing it.
            if not args.yes:
                print(
                    f"This will DROP '{config.tools_collection}' and restore "
                    f"'{archive_name(config, args.run_id)}' in its place."
                )
                if input("Type 'yes' to continue: ").strip().lower() != "yes":
                    print("Aborted.")
                    return 1

            result = rollback_run(args.run_id, config, repos)
            print(f"Restored {result['restored_from']} -> {result['promoted']}")
            return 0

        if args.command == "runs":
            if args.runs_command == "list":
                runs = list_runs(
                    workdir=Path(args.workdir),
                    runs_root=args.runs_root,
                )
                if args.json:
                    print(json.dumps(runs, indent=2))
                else:
                    _print_runs_table(runs)
                return 0

            if args.runs_command == "show":
                data = show_run(
                    args.run_ref,
                    workdir=Path(args.workdir),
                    runs_root=args.runs_root,
                )
                if args.json:
                    print(json.dumps(data, indent=2))
                else:
                    _print_run_summary(data)
                return 0

            if args.runs_command == "latest":
                data = get_latest_run(
                    workdir=Path(args.workdir),
                    runs_root=args.runs_root,
                )
                if args.json:
                    print(json.dumps(data, indent=2))
                else:
                    _print_run_summary(data)
                return 0

        if args.command == "scheduler":
            from dotenv import load_dotenv

            from adapters.scheduler.runner import run_job_now, start_scheduler
            from infrastructure.config import PipelineConfig

            load_dotenv(args.env_file)
            config = PipelineConfig.from_env()
            if args.scheduler_command == "start":
                start_scheduler(config)
            elif args.scheduler_command == "run-now":
                run_job_now(args.job)
            return 0

        return 0

    except PipelineError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())