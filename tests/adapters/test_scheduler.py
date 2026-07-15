"""Offline tests for the scheduler adapter.

No live clock, no sleep, no network: the job is checked by faking ``run_full``,
and the runner is checked by inspecting registered jobs without starting it.
"""

from __future__ import annotations

import pytest

from adapters.scheduler import runner
from adapters.scheduler.jobs import run_full_pipeline_job
from adapters.scheduler.runner import build_scheduler, run_job_now
from infrastructure.config import PipelineConfig


def test_full_pipeline_job_invokes_run_with_expected_argv(monkeypatch):
    """The job shells out to `rsetl run --no-human-updates --tag scheduled`."""
    calls = []

    def fake_run_full(**kwargs):
        calls.append(kwargs)

    # run_full is imported by name into adapters.cli.main (main.py:11), so that
    # is the object main() looks up -- patch it there, never with a `src.` prefix.
    monkeypatch.setattr("adapters.cli.main.run_full", fake_run_full)

    run_full_pipeline_job()

    assert len(calls) == 1
    assert calls[0]["human_updates"] is False
    assert calls[0]["run_tag"] == "scheduled"


def test_build_scheduler_registers_the_full_pipeline_job():
    config = PipelineConfig(full_pipeline_cron="0 1 * * mon,thu")

    scheduler = build_scheduler(config)

    # get_job finds pending jobs even though the scheduler was never started.
    assert scheduler.get_job("full_pipeline") is not None


def test_run_job_now_dispatches_by_name(monkeypatch):
    fired = []
    monkeypatch.setitem(runner.JOBS, "full_pipeline", lambda: fired.append(True))

    run_job_now("full_pipeline")

    assert fired == [True]


def test_run_job_now_rejects_unknown_job():
    with pytest.raises(ValueError):
        run_job_now("does_not_exist")
