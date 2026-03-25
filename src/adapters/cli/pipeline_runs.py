from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from adapters.cli.pipeline_full import PipelineError


def load_run_manifest(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        return {}

    try:
        with open(manifest_path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def resolve_run_dir(run_ref: str | Path, runs_root: Path) -> Path:
    candidate = Path(run_ref)

    if candidate.exists():
        return candidate.resolve()

    candidate2 = (runs_root / str(run_ref)).resolve()
    if candidate2.exists():
        return candidate2

    raise PipelineError(
        f"Could not resolve run reference {run_ref!r}. "
        f"Use a run ID under {runs_root} or a full run directory path."
    )


def latest_run_dir(runs_root: Path) -> Path:
    if not runs_root.exists():
        raise PipelineError(f"Runs root does not exist: {runs_root}")

    run_dirs = [
        p for p in runs_root.iterdir()
        if p.is_dir() and p.name != "latest"
    ]
    if not run_dirs:
        raise PipelineError(f"No runs found under {runs_root}")

    run_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return run_dirs[0]


def _default_paths_for_run(run_dir: Path) -> dict[str, str]:
    run_id = run_dir.name
    return {
        "grouped_entries_file": str(run_dir / f"grouped_entries.{run_id}.json"),
        "grouped_entries_no_opeb": str(run_dir / f"grouped_entries.no_opeb_metrics.{run_id}.json"),
        "conflicts_json": str(run_dir / f"conflicts.{run_id}.json"),
        "simplified_blocks_json": str(run_dir / f"grouped_entries.simplified.{run_id}.json"),
        "conflicts_jsonl": str(run_dir / f"conflicts.{run_id}.jsonl"),
        "simplified_blocks_jsonl": str(run_dir / f"grouped_entries.simplified.{run_id}.jsonl"),
        "disambiguation_out_dir": str(run_dir / f"disambiguation.{run_id}.jsonl"),
    }


def get_run_status(run_dir: Path) -> dict[str, Any]:
    manifest = load_run_manifest(run_dir)
    run_id = run_dir.name

    paths = manifest.get("paths", _default_paths_for_run(run_dir))
    execution_history = manifest.get("execution_history", [])
    latest_execution = manifest.get("latest_execution") or (execution_history[-1] if execution_history else {})
    latest_stage_selection = latest_execution.get("stage_selection", {})
    latest_executed_stages = (
        manifest.get("latest_executed_stages")
        or latest_stage_selection.get("executed_stages", [])
    )

    disambiguation_exists = Path(paths["disambiguation_out_dir"]).exists()
    resumable = bool(execution_history) or disambiguation_exists

    return {
        "run_id": manifest.get("run_id", run_id),
        "run_dir": str(run_dir),
        "created_utc": manifest.get("created_utc"),
        "last_updated_utc": manifest.get("last_updated_utc"),
        "has_manifest": bool(manifest),
        "disambiguation_exists": disambiguation_exists,
        "latest_executed_stages": latest_executed_stages,
        "resumable": resumable,
        "execution_count": len(execution_history),
    }


def list_runs(workdir: str | Path = ".", runs_root: str | Path = "data/integration/runs") -> list[dict[str, Any]]:
    wd = Path(workdir).resolve()
    runs_root = (wd / runs_root).resolve()

    if not runs_root.exists():
        return []

    runs = []
    for child in sorted(runs_root.iterdir(), reverse=True):
        if not child.is_dir():
            continue
        if child.name == "latest":
            continue
        runs.append(get_run_status(child))

    runs.sort(
        key=lambda x: (x.get("last_updated_utc") or x.get("created_utc") or ""),
        reverse=True,
    )
    return runs


def show_run(run_ref: str, workdir: str | Path = ".", runs_root: str | Path = "data/integration/runs") -> dict[str, Any]:
    wd = Path(workdir).resolve()
    runs_root = (wd / runs_root).resolve()

    run_dir = resolve_run_dir(run_ref, runs_root)
    manifest = load_run_manifest(run_dir)

    if manifest:
        return manifest

    return {
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "paths": _default_paths_for_run(run_dir),
        "warning": "No manifest.json found for this run.",
    }


def get_latest_run(workdir: str | Path = ".", runs_root: str | Path = "data/integration/runs") -> dict[str, Any]:
    wd = Path(workdir).resolve()
    runs_root = (wd / runs_root).resolve()
    run_dir = latest_run_dir(runs_root)
    return show_run(run_dir, workdir=wd, runs_root=runs_root)