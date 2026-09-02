'''
rsetl run-transformation
rsetl run-transformation --tag test1
rsetl run-transformation --sources all
rsetl run-transformation --workdir . --runs-root data/integration/runs
''' 

from __future__ import annotations

import argparse
import json
import os
import sys
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


def run_transformation(
    workdir: str | Path = ".",
    runs_root: str | Path = "data/integration/runs",
    run_tag: Optional[str] = None,
    sources: str = "all",
    updated_within_days: int = 30,
    python_exe: str = "python",
) -> None:
    """
    Run only the transformation step and store provenance information.

    Outputs are placed under: <runs_root>/<run_id>/
    A convenience symlink 'latest' is maintained in <runs_root>/.
    """
    wd = Path(workdir).resolve()
    runs_root = (wd / runs_root).resolve()
    runs_root.mkdir(parents=True, exist_ok=True)

    run_id = _make_run_id(wd, tag=run_tag)
    run_dir = runs_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    _symlink_latest(runs_root / "latest", run_dir)

    manifest_path = run_dir / "manifest.transformation.json"

    started_at = datetime.now(timezone.utc)

    print("=== Stage 0/0: Transformation ===")
    _require_env(["MONGO_HOST", "MONGO_PORT", "MONGO_USER", "MONGO_PWD", "MONGO_AUTH_SRC", "MONGO_DB"])

    _run(
        [
            python_exe,
            "-m",
            "src.adapters.cli.transformation.transformation",
            "--sources",
            sources,
            "--updated-within-days",
            str(updated_within_days),
        ],
        cwd=wd,
    )

    manifest = {
        "pipeline": "transformation-only",
        "run_id": run_id,
        "run_dir": str(run_dir),
        "git_short_sha": _git_short_sha(wd),
        "utc_started": started_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "utc_finished": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "options": {
            "sources": sources,
            "updated_within_days": updated_within_days,
        },
        "env_used": {
            "MONGO_HOST": os.getenv("MONGO_HOST"),
            "MONGO_PORT": os.getenv("MONGO_PORT"),
            "MONGO_USER": os.getenv("MONGO_USER"),
            "MONGO_DB": os.getenv("MONGO_DB"),
            "MONGO_AUTH_SRC": os.getenv("MONGO_AUTH_SRC"),
            "MONGO_PWD": mask_secret(os.getenv("MONGO_PWD")),
        },
    }

    try:
        with open(manifest_path, "w") as fh:
            json.dump(manifest, fh, indent=2)
    except Exception:
        pass

    print(f"Transformation completed. Run directory: {run_dir}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run only the transformation step")
    parser.add_argument("--tag", dest="run_tag", help="Optional tag appended to run ID")
    parser.add_argument("--sources", default="all", help="Sources passed to the transformation step")
    parser.add_argument(
        "--updated-within-days",
        type=int,
        default=30,
        dest="updated_within_days",
        help="Only transform raw entries updated within the last N days (default: 30). Use 0 for a full re-transform.",
    )
    parser.add_argument("--python-exe", default="python", help="Python executable for subprocesses")
    parser.add_argument("--workdir", default=".", help="Working directory")
    parser.add_argument("--runs-root", default="data/integration/runs", help="Root folder for run outputs")
    args = parser.parse_args(argv)

    run_transformation(
        workdir=args.workdir,
        runs_root=args.runs_root,
        run_tag=args.run_tag,
        sources=args.sources,
        updated_within_days=args.updated_within_days,
        python_exe=args.python_exe,
    )
    return 0

if __name__ == "__main__":
    sys.exit(main())