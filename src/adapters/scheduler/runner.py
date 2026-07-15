"""APScheduler setup for the pipeline jobs.

``BlockingScheduler`` runs in the foreground under ``rsetl scheduler start``.
Registration is split from starting so the schedule can be inspected without a
live clock (see ``build_scheduler``).
"""

from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from adapters.scheduler.jobs import run_full_pipeline_job
from infrastructure.config import PipelineConfig

# The publication-enrichment job joins this map in item 8.
JOBS = {"full_pipeline": run_full_pipeline_job}


def build_scheduler(config: PipelineConfig) -> BlockingScheduler:
    """Build a scheduler with every job registered, but do not start it."""
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_full_pipeline_job,
        trigger=CronTrigger.from_crontab(config.full_pipeline_cron),
        id="full_pipeline",
        # Two pipeline runs must never overlap: they both promote into toolsDev.
        max_instances=1,
        misfire_grace_time=3600,
        replace_existing=True,
    )
    return scheduler


def start_scheduler(config: PipelineConfig) -> None:
    """Start the scheduler in the foreground (blocks until interrupted)."""
    build_scheduler(config).start()


def run_job_now(name: str) -> None:
    """Trigger one job immediately, by id."""
    try:
        job = JOBS[name]
    except KeyError:
        raise ValueError(
            f"Unknown job {name!r}. Known jobs: {', '.join(sorted(JOBS))}"
        ) from None
    job()
