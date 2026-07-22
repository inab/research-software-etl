"""
Promote a finished run's tools into place.

Merge builds into a staging collection so the live one stays readable throughout
-- it is where the new entries inherit their ids from. Finalizing swaps them:

    toolsDev      -> toolsDev_archive_<run_id>
    toolsDev_next -> toolsDev

Each rename is atomic in MongoDB. There is a brief window between the two where
the live collection does not exist; the tools collection is read by dashboards,
not by a latency-sensitive API, so that gap is acceptable.

The archive is what makes ``rollback`` possible, and it is the only copy of the
ids this run retired.
"""

import logging

from infrastructure.config import PipelineConfig
from domain.repositories import Repositories

logger = logging.getLogger("rs-etl-pipeline")


class FinalizeRunError(RuntimeError):
    pass


def archive_name(config: PipelineConfig, run_id: str) -> str:
    return f"{config.tools_archive_prefix}{run_id}"


def finalize_run(run_id: str, config: PipelineConfig, repos: Repositories) -> dict:
    """Archive the live tools collection and promote the staging one in its place."""
    if not repos.tools_staging.exists():
        raise FinalizeRunError(
            f"nothing to promote: staging collection "
            f"'{config.tools_staging_collection}' does not exist. Run the merge stage first."
        )

    archive = archive_name(config, run_id)
    had_live = repos.tools.exists()

    if had_live:
        logger.info("Archiving '%s' as '%s'", config.tools_collection, archive)
        repos.tools.rename_to(archive)

    logger.info(
        "Promoting '%s' to '%s'",
        config.tools_staging_collection,
        config.tools_collection,
    )
    repos.tools_staging.rename_to(config.tools_collection)

    pruned = _prune_archives(config, repos)

    return {
        "archived_as": archive if had_live else None,
        "promoted": config.tools_collection,
        "pruned": pruned,
    }


def _prune_archives(config: PipelineConfig, repos: Repositories) -> list[str]:
    """
    Drop all but the newest ``tools_archive_keep`` archives.

    Run ids are timestamp-prefixed, so a reverse lexicographic sort of the archive
    names is newest-first -- no date parsing needed. Returns the names dropped.

    ``keep < 1`` is refused: it would drop the archive this run just created and
    leave the run with no rollback target.
    """
    keep = config.tools_archive_keep
    if keep < 1:
        logger.warning(
            "tools_archive_keep=%s < 1; keeping all archives so this run stays "
            "rollback-able",
            keep,
        )
        return []

    archives = sorted(
        repos.tools.list_by_prefix(config.tools_archive_prefix), reverse=True
    )
    stale = archives[keep:]
    for name in stale:
        logger.info("Dropping stale archive '%s' (keeping newest %s)", name, keep)
        repos.tools.for_collection(name).drop()
    return stale


def rollback_run(run_id: str, config: PipelineConfig, repos: Repositories) -> dict:
    """
    Undo a finalize: put the archived collection back in place.

    The live collection this replaces is dropped, not archived again -- it is the
    output of the run being rolled back, and keeping it would leave a second copy
    of data the operator has just declared wrong.
    """
    archive = repos.tools.for_collection(archive_name(config, run_id))

    if not archive.exists():
        raise FinalizeRunError(
            f"no archive to roll back to: '{archive.collection_name}' does not exist"
        )

    if repos.tools.exists():
        logger.warning(
            "Dropping the current '%s' and restoring '%s'",
            config.tools_collection,
            archive.collection_name,
        )
        repos.tools.drop()

    archive.rename_to(config.tools_collection)

    return {
        "restored_from": archive.collection_name,
        "promoted": config.tools_collection,
    }
