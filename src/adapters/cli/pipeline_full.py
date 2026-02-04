# adapters/cli/main.py
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


def _require_env(vars_: Sequence[str]) -> None:
    missing = [v for v in vars_ if not os.getenv(v)]
    if missing:
        raise PipelineError(f"Missing required environment variables: {', '.join(missing)}")


def _run(cmd: Sequence[str] | str, cwd: Optional[Path] = None, extra_env: Optional[dict] = None) -> None:
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
        latest_path.symlink_to(target.name)  # relative link inside runs/
    except Exception:
        # Non-fatal on filesystems without symlink support
        pass

def mask_secret(
    secret: Optional[str],
    *,
    keep_start: int = 3,
    keep_end: int = 3,
    min_length: int = 8,
    mask_char: str = "*",
) -> str:
    """
    Mask a secret while keeping a small prefix/suffix for identification.

    Examples:
      "abcdEFGHijkl" -> "abc……jkl"
      "short" -> "<hidden>"
    """
    if not secret:
        return "<hidden>"

    s = str(secret).strip()

    if len(s) < min_length or keep_start + keep_end >= len(s):
        return "<hidden>"

    return (
        s[:keep_start]
        + mask_char * (len(s) - keep_start - keep_end)
        + s[-keep_end:]
    )



def run_full(
    workdir: str | Path = ".",
    # where to store versioned outputs
    runs_root: str | Path = "data/integration/runs",
    run_tag: Optional[str] = None,  # optional human tag added to run_id
    # Stage toggles and options
    remove_opeb_metrics: bool = True,
    human_updates: bool = True,
    do_merge_to_db: bool = True,
    python_exe: str = "python",
) -> None:
    """
    Run the full integration pipeline with per-run versioned outputs.

    Outputs are placed under: <runs_root>/<run_id>/
    A convenience symlink 'latest' is maintained in <runs_root>/.

    Required env vars:
      Mongo (Stage 1 & 8): MONGO_HOST, MONGO_PORT, MONGO_USER, MONGO_PWD, MONGO_AUTH_SRC, MONGO_DB
      Tokens (Stage 6):   GITHUB_TOKEN, GITLAB_TOKEN, OPENROUTER_API_KEY, HUGGINGFACE_API_KEY
    """
    wd = Path(workdir).resolve()
    runs_root = (wd / runs_root).resolve()
    runs_root.mkdir(parents=True, exist_ok=True)

    run_id = _make_run_id(wd, tag=run_tag)
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # Keep a handy "latest" pointer
    _symlink_latest(runs_root / "latest", run_dir)

    # Define all versioned paths for this run
    grouped_entries_file        = run_dir / f"grouped_entries.{run_id}.json"
    grouped_entries_no_opeb     = run_dir / f"grouped_entries.no_opeb_metrics.{run_id}.json"
    conflicts_json              = run_dir / f"conflicts.{run_id}.json"
    simplified_blocks_json      = run_dir / f"grouped_entries.simplified.{run_id}.json"
    conflicts_jsonl             = run_dir / f"conflicts.{run_id}.jsonl"
    simplified_blocks_jsonl     = run_dir / f"grouped_entries.simplified.{run_id}.jsonl"
    # for now the pair_wise_decisions_file is hardcoded
    pair_wise_decisions_file    = "/Users/evabsc/projects/software-observatory/research-software-etl/src/application/services/integration/disambiguation/pair_decisions.jsonl"
    disambiguation_out_dir      = run_dir / f"disambiguation.{run_id}.jsonl"
    #disambiguation_out_dir.mkdir(parents=True, exist_ok=True)

    manifest_path               = run_dir / "manifest.json"

    # ── Stage 1 ──────────────────────────────────────────────────────────────────
    # This step should be the TRANSFORMATION
    
    print("=== Stage 1/8: Blocking + recovery ===")
    _require_env(["MONGO_HOST", "MONGO_PORT", "MONGO_USER", "MONGO_PWD", "MONGO_AUTH_SRC", "MONGO_DB"])
    _run([
        python_exe, "-m", "src.adapters.cli.integration.group_and_recovery",
        "--grouped-entries-file", str(grouped_entries_file),
    ], cwd=wd)
    
    
    # ── Stage 2 (optional) ──────────────────────────────────────────────────────
    effective_blocks_in = grouped_entries_file
    if remove_opeb_metrics:
        print("=== Stage 2/8: Remove OpenEBench 'metrics' (optional) ===")
        _run([
            python_exe, "scripts/remove_oeb_metrics.py",
            "--in", str(grouped_entries_file),
            "--out", str(grouped_entries_no_opeb),
        ], cwd=wd)
        effective_blocks_in = grouped_entries_no_opeb

    
    # ── Stage 3 ──────────────────────────────────────────────────────────────────
    print("=== Stage 3/8: Conflict detection ===")
    _run([
        python_exe, "-m", "src.adapters.cli.integration.conflict_detection",
        "--grouped-entries-file", str(effective_blocks_in),
        "--disconnected-entries-file", str(conflicts_json),
    ], cwd=wd)

    
    # ── Stage 4 ──────────────────────────────────────────────────────────────────
    print("=== Stage 4/8: Simplify blocks ===")
    _run([
        python_exe, "scripts/simplify_grouped_entries.py",
        "--in", str(grouped_entries_file),
        "--out", str(simplified_blocks_json),
    ], cwd=wd)

    
    # ── Stage 5 ──────────────────────────────────────────────────────────────────
    print("=== Stage 5/8: Convert JSON → JSONL (conflicts & simplified blocks) ===")
    _run([
        python_exe, "scripts/json_to_jsonl.py",
        "--in", str(conflicts_json),
        "--out", str(conflicts_jsonl),
    ], cwd=wd)
    _run([
        python_exe, "scripts/json_to_jsonl.py",
        "--in", str(simplified_blocks_json),
        "--out", str(simplified_blocks_jsonl),
    ], cwd=wd)

    
    # ── Stage 6 ──────────────────────────────────────────────────────────────────
    print("=== Stage 6/8: Disambiguation (LLM + heuristics + GH issues) ===")
    _require_env(["GITHUB_TOKEN", "GITLAB_TOKEN", "OPENROUTER_API_KEY", "HUGGINGFACE_API_KEY"])
    _run([
        python_exe, "-m", "src.adapters.cli.integration.disambiguation",
        "--conflict-blocks-file", str(conflicts_jsonl),
        "--blocks-file", str(simplified_blocks_jsonl),
        "--disambiguated-blocks-file", str(disambiguation_out_dir),
        "--pair_wise_decisions_file", str(pair_wise_decisions_file),
        "--run-id", run_id
    ], cwd=wd)

    '''
    # ── Stage 7 ──────────────────────────────────────────────────────────────────
    if human_updates:
        print("=== Stage 7/8: Update disambiguation after human resolution ===")
        try:
            _run(["git", "pull"], cwd=wd)
        except PipelineError:
            print("… git pull skipped/failed; continuing.")
        _run([
            python_exe, "-m", "src.adapters.cli.integration.update_disambiguation_after_human_resoltion",
            "--disambiguation-dir", str(disambiguation_out_dir),
        ], cwd=wd)

    # ── Stage 8 ──────────────────────────────────────────────────────────────────
    if do_merge_to_db:
        print("=== Stage 8/8: Merge entries into DB ===")
        _run([
            python_exe, "-m", "src.adapters.cli.integration.merge_entries",
            "--disambiguation-dir", str(disambiguation_out_dir),
        ], cwd=wd)

    # -- Stage 9 ------------------------------------------------------------------
    # Calculation of statistics and FAIRness

    # TODO

    '''
    # ── Manifest ─────────────────────────────────────────────────────────────────
    manifest = {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "git_short_sha": _git_short_sha(wd),
        "utc_started": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
            "HUGGINGFACE_API_KEY": mask_secret(os.getenv("HUGGINGFACE_API_KEY"))         
        },
    }
    try:
        with open(manifest_path, "w") as fh:
            json.dump(manifest, fh, indent=2)
    except Exception:
        pass
        

    print(f"Pipeline completed. Run directory: {run_dir}")