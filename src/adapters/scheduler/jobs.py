"""Scheduled job definitions.

Each job is deliberately thin: it shells out to the same ``rsetl`` entry point a
human would use, rather than reconstructing the pipeline in-process. ``run_full``
already runs every stage as a subprocess, so the job has nothing to orchestrate.
"""

from __future__ import annotations

import logging

from adapters.cli.main import main

logger = logging.getLogger(__name__)


def run_full_pipeline_job() -> None:
    """Phase A: stages 1-8, then 10-12. Stage 9 (human updates) is skipped.

    ``main`` returns an exit code and swallows ``PipelineError`` (returning 1),
    so a failed run does not raise here. We check the code and log it instead,
    which keeps the scheduler alive for the next firing either way.
    """
    code = main(["run", "--no-human-updates", "--tag", "scheduled"])
    if code != 0:
        logger.error("Scheduled full pipeline run failed with exit code %s", code)
