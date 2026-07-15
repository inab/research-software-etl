"""Scheduled job definitions.

Jobs are deliberately thin. The full-pipeline job shells out to the same
``rsetl`` entry point a human would use, because ``run_full`` already runs every
stage as a subprocess. The publication-enrichment job is a single in-process use
case, so it builds config + repos and calls the shared factory directly.
"""

from __future__ import annotations

import logging

from adapters.cli.enrich_publications import build_enrich_publications_use_case
from adapters.cli.main import main
from infrastructure.config import PipelineConfig
from infrastructure.db.repositories import from_config

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


def run_publication_enrichment_job() -> None:
    """Re-enrich publication metadata + citation counts from Europe PMC.

    Runs with ``skip_seen=False`` so the DB-state predicate is the sole gate:
    records whose Europe PMC count is total-only (no per-year breakdown) get
    re-enriched even if their DOI is already in the local cache. Any failure is
    logged rather than raised, keeping the scheduler alive.
    """
    try:
        config = PipelineConfig.from_env()
        repos = from_config(config)
        use_case = build_enrich_publications_use_case(config, repos)
        use_case.execute(skip_seen=False)
    except Exception:
        logger.exception("Scheduled publication enrichment run failed")
