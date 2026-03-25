from __future__ import annotations

import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
from dotenv import load_dotenv

load_dotenv()


class PipelineError(RuntimeError):
    pass


STAGES = [
    "transformation",
    "grouping",
    "remove_opeb_metrics",
    "conflict_detection",
    "simplify_blocks",
    "json_to_jsonl",
    "disambiguation",
    "human_updates",
    "merge",
    "stats",
]


def _require_env(vars_: Sequence[str]) -> None:
    missing = [v for v in vars_ if not os.getenv(v)]
    if missing:
        raise PipelineError(f"Missing required environment variables: {', '.join(missing)}")


def _run(
    cmd: Sequence[str] | str,
    cwd: Optional[Path] = None,
    extra_env: Optional[dict] = None,
) -> None:
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    print(f"→ Running: {' '.join(shlex.quote(c) for c in cmd)}")
    try:
        subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, check=True)
    except subprocess.CalledProcessError as e:
        raise PipelineError(f"Command failed ({e.returncode}): {' '.join(cmd)}") from e


def _git_short_sha(cwd: Path) -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(cwd))
        return out.decode().strip()
    except Exception:
        return "nogit"


def _make_run_id(cwd: Path, tag: Optional[str] = None) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    sha = _git_short_sha(cwd)
    parts = [ts, sha]
    if tag:
        parts.append(tag)
    return "-".join(parts)


def _symlink_latest(latest_path: Path, target: Path) -> None:
    try:
        if latest_path.exists() or latest_path.is_symlink():
            latest_path.unlink()
        latest_path.symlink_to(target.name)
    except Exception:
        pass


def mask_secret(
    secret: Optional[str],
    *,
    keep_start: int = 3,
    keep_end: int = 3,
    min_length: int = 8,
    mask_char: str = "*",
) -> str:
    if not secret:
        return "<hidden>"

    s = str(secret).strip()

    if len(s) < min_length or keep_start + keep_end >= len(s):
        return "<hidden>"

    return s[:keep_start] + mask_char * (len(s) - keep_start - keep_end) + s[-keep_end:]


def _validate_stage(stage: str, arg_name: str) -> None:
    if stage not in STAGES:
        raise PipelineError(
            f"Invalid value for {arg_name}: {stage!r}. "
            f"Valid stages are: {', '.join(STAGES)}"
        )


def _resolve_selected_stages(
    *,
    from_stage: Optional[str] = None,
    until_stage: Optional[str] = None,
    only_stage: Optional[str] = None,
    remove_opeb_metrics: bool = True,
    human_updates: bool = True,
    do_merge_to_db: bool = True,
) -> list[str]:
    if only_stage:
        _validate_stage(only_stage, "--only")
        selected = [only_stage]
    else:
        if from_stage:
            _validate_stage(from_stage, "--from-stage")
        if until_stage:
            _validate_stage(until_stage, "--until")

        start_idx = STAGES.index(from_stage) if from_stage else 0
        end_idx = STAGES.index(until_stage) if until_stage else len(STAGES) - 1

        if start_idx > end_idx:
            raise PipelineError("--from-stage must come before or equal to --until")

        selected = STAGES[start_idx : end_idx + 1]

    # Apply feature toggles
    if not remove_opeb_metrics and "remove_opeb_metrics" in selected:
        selected.remove("remove_opeb_metrics")
    if not human_updates and "human_updates" in selected:
        selected.remove("human_updates")
    if not do_merge_to_db and "merge" in selected:
        selected.remove("merge")

    return selected


def run_full(
    workdir: str | Path = ".",
    runs_root: str | Path = "data/integration/runs",
    run_tag: Optional[str] = None,
    remove_opeb_metrics: bool = True,
    human_updates: bool = True,
    do_merge_to_db: bool = True,
    python_exe: str = "python",
    from_stage: Optional[str] = None,
    until_stage: Optional[str] = None,
    only_stage: Optional[str] = None,
) -> None:
    wd = Path(workdir).resolve()
    runs_root = (wd / runs_root).resolve()
    runs_root.mkdir(parents=True, exist_ok=True)

    run_id = _make_run_id(wd, tag=run_tag)
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    _symlink_latest(runs_root / "latest", run_dir)

    grouped_entries_file = run_dir / f"grouped_entries.{run_id}.json"
    grouped_entries_no_opeb = run_dir / f"grouped_entries.no_opeb_metrics.{run_id}.json"
    conflicts_json = run_dir / f"conflicts.{run_id}.json"
    simplified_blocks_json = run_dir / f"grouped_entries.simplified.{run_id}.json"
    conflicts_jsonl = run_dir / f"conflicts.{run_id}.jsonl"
    simplified_blocks_jsonl = run_dir / f"grouped_entries.simplified.{run_id}.jsonl"

    pair_wise_decisions_file = (
        "/Users/evabsc/projects/software-observatory/research-software-etl/"
        "src/application/services/integration/disambiguation/pair_decisions.jsonl"
    )

    disambiguation_out_dir = run_dir / f"disambiguation.{run_id}.jsonl"
    disambiguation_out_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = run_dir / "manifest.json"

    started_at = datetime.now(timezone.utc)

    selected_stages = _resolve_selected_stages(
        from_stage=from_stage,
        until_stage=until_stage,
        only_stage=only_stage,
        remove_opeb_metrics=remove_opeb_metrics,
        human_updates=human_updates,
        do_merge_to_db=do_merge_to_db,
    )

    executed_stages: list[str] = []

    def should_run(stage: str) -> bool:
        return stage in selected_stages

    # Stage 0
    if should_run("transformation"):
        print("=== Stage: transformation ===")
        _require_env(["MONGO_HOST", "MONGO_PORT", "MONGO_USER", "MONGO_PWD", "MONGO_AUTH_SRC", "MONGO_DB"])
        _run(
            [python_exe, "-m", "src.adapters.cli.transformation.transformation", "--sources", "all"],
            cwd=wd,
        )
        executed_stages.append("transformation")

    # Stage 1
    if should_run("grouping"):
        print("=== Stage: grouping ===")
        _require_env(["MONGO_HOST", "MONGO_PORT", "MONGO_USER", "MONGO_PWD", "MONGO_AUTH_SRC", "MONGO_DB"])
        _run(
            [
                python_exe,
                "-m",
                "src.adapters.cli.integration.group_and_recovery",
                "--grouped-entries-file",
                str(grouped_entries_file),
            ],
            cwd=wd,
        )
        executed_stages.append("grouping")

    effective_blocks_in = grouped_entries_file

    # Stage 2
    if should_run("remove_opeb_metrics"):
        print("=== Stage: remove_opeb_metrics ===")
        _run(
            [
                python_exe,
                "scripts/scripts/remove_oeb_metrics.py",
                "--in",
                str(grouped_entries_file),
                "--out",
                str(grouped_entries_no_opeb),
            ],
            cwd=wd,
        )
        effective_blocks_in = grouped_entries_no_opeb
        executed_stages.append("remove_opeb_metrics")
    elif grouped_entries_no_opeb.exists():
        # useful when resuming later in a run directory
        effective_blocks_in = grouped_entries_no_opeb

    # Stage 3
    if should_run("conflict_detection"):
        print("=== Stage: conflict_detection ===")
        _run(
            [
                python_exe,
                "-m",
                "src.adapters.cli.integration.conflict_detection",
                "--grouped-entries-file",
                str(effective_blocks_in),
                "--disconnected-entries-file",
                str(conflicts_json),
            ],
            cwd=wd,
        )
        executed_stages.append("conflict_detection")

    # Stage 4
    if should_run("simplify_blocks"):
        print("=== Stage: simplify_blocks ===")
        _run(
            [
                python_exe,
                "scripts/utils/simplify_grouped_entries.py",
                "--in",
                str(effective_blocks_in),
                "--out",
                str(simplified_blocks_json),
            ],
            cwd=wd,
        )
        executed_stages.append("simplify_blocks")

    # Stage 5
    if should_run("json_to_jsonl"):
        print("=== Stage: json_to_jsonl ===")
        _run(
            [
                python_exe,
                "scripts/utils/json_to_jsonl.py",
                "--in",
                str(conflicts_json),
                "--out",
                str(conflicts_jsonl),
            ],
            cwd=wd,
        )
        _run(
            [
                python_exe,
                "scripts/utils/json_to_jsonl.py",
                "--in",
                str(simplified_blocks_json),
                "--out",
                str(simplified_blocks_jsonl),
            ],
            cwd=wd,
        )
        executed_stages.append("json_to_jsonl")

    # Stage 6
    if should_run("disambiguation"):
        print("=== Stage: disambiguation ===")
        _require_env(["GITHUB_TOKEN", "GITLAB_TOKEN", "OPENROUTER_API_KEY", "HUGGINGFACE_API_KEY"])
        _run(
            [
                python_exe,
                "-m",
                "src.adapters.cli.integration.disambiguation",
                "--conflict-blocks-file",
                str(conflicts_jsonl),
                "--blocks-file",
                str(simplified_blocks_jsonl),
                "--disambiguated-blocks-file",
                str(disambiguation_out_dir),
                "--pair_wise_decisions_file",
                str(pair_wise_decisions_file),
                "--run-id",
                run_id,
            ],
            cwd=wd,
        )
        executed_stages.append("disambiguation")

    # Stage 7
    if should_run("human_updates"):
        print("=== Stage: human_updates ===")
        try:
            _run(["git", "pull"], cwd=wd)
        except PipelineError:
            print("… git pull skipped/failed; continuing.")
        _run(
            [
                python_exe,
                "-m",
                "src.adapters.cli.integration.update_disambiguation_after_human_resoltion",
                "--disambiguation-dir",
                str(disambiguation_out_dir),
            ],
            cwd=wd,
        )
        executed_stages.append("human_updates")

    # Stage 8
    if should_run("merge"):
        print("=== Stage: merge ===")
        _require_env(["MONGO_HOST", "MONGO_PORT", "MONGO_USER", "MONGO_PWD", "MONGO_AUTH_SRC", "MONGO_DB"])
        _run(
            [
                python_exe,
                "-m",
                "src.adapters.cli.integration.merge_entries",
                "--disambiguated-blocks-file",
                str(disambiguation_out_dir),
            ],
            cwd=wd,
        )
        executed_stages.append("merge")

    # Stage 9
    if should_run("stats"):
        print("=== Stage: stats ===")
        _require_env(["MONGO_HOST", "MONGO_PORT", "MONGO_USER", "MONGO_PWD", "MONGO_AUTH_SRC", "MONGO_DB"])
        _run(
            [python_exe, "-m", "src.adapters.cli.generate_stats", "--collections", "tools"],
            cwd=wd,
        )
        executed_stages.append("stats")

    manifest = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "git_short_sha": _git_short_sha(wd),
        "utc_started": started_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "utc_finished": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stage_selection": {
            "from_stage": from_stage,
            "until_stage": until_stage,
            "only_stage": only_stage,
            "selected_stages": selected_stages,
            "executed_stages": executed_stages,
        },
        "paths": {
            "grouped_entries_file": str(grouped_entries_file),
            "grouped_entries_no_opeb": str(grouped_entries_no_opeb),
            "conflicts_json": str(conflicts_json),
            "simplified_blocks_json": str(simplified_blocks_json),
            "conflicts_jsonl": str(conflicts_jsonl),
            "simplified_blocks_jsonl": str(simplified_blocks_jsonl),
            "disambiguation_out_dir": str(disambiguation_out_dir),
        },
        "options": {
            "remove_opeb_metrics": remove_opeb_metrics,
            "human_updates": human_updates,
            "do_merge_to_db": do_merge_to_db,
        },
        "env_used": {
            "MONGO_HOST": os.getenv("MONGO_HOST"),
            "MONGO_PORT": os.getenv("MONGO_PORT"),
            "MONGO_USER": os.getenv("MONGO_USER"),
            "MONGO_DB": os.getenv("MONGO_DB"),
            "MONGO_AUTH_SRC": os.getenv("MONGO_AUTH_SRC"),
            "MONGO_PWD": mask_secret(os.getenv("MONGO_PWD")),
            "GITHUB_TOKEN": mask_secret(os.getenv("GITHUB_TOKEN")),
            "GITLAB_TOKEN": mask_secret(os.getenv("GITLAB_TOKEN")),
            "OPENROUTER_API_KEY": mask_secret(os.getenv("OPENROUTER_API_KEY")),
            "HUGGINGFACE_API_KEY": mask_secret(os.getenv("HUGGINGFACE_API_KEY")),
        },
    }

    try:
        with open(manifest_path, "w") as fh:
            json.dump(manifest, fh, indent=2)
    except Exception:
        pass

    print(f"Pipeline completed. Run directory: {run_dir}")