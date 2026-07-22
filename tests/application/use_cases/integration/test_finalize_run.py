"""
Archive retention in finalize_run (roadmap item 3a).

Every finalize archives the live tools collection as ``tools_archive_<run_id>``.
Without pruning these accumulate one per scheduled run; ``tools_archive_keep``
caps how many are kept. Run ids are timestamp-prefixed, so a lexicographic sort
is chronological and the newest survive.
"""

import pytest

from application.use_cases.integration.finalize_run import finalize_run, rollback_run
from infrastructure.config import PipelineConfig
from tests.fakes import FakeDatabaseAdapter, fake_repos


# Timestamp-prefixed run ids, oldest to newest.
OLD_RUNS = [
    "20260101T000000Z-aaa",
    "20260201T000000Z-bbb",
    "20260301T000000Z-ccc",
    "20260401T000000Z-ddd",
]
NEW_RUN = "20260701T000000Z-eee"


def _config(keep: int = 2) -> PipelineConfig:
    return PipelineConfig(
        tools_collection="tools",
        tools_staging_collection="tools_next",
        tools_archive_prefix="tools_archive_",
        tools_archive_keep=keep,
    )


def _db_with_archives(old_runs) -> FakeDatabaseAdapter:
    """A live collection, a built staging one, and one archive per old run."""
    collections = {
        "tools": [{"_id": "live", "data": {"name": "live"}}],
        "tools_next": [{"_id": "staged", "data": {"name": "staged"}}],
    }
    for run in old_runs:
        collections[f"tools_archive_{run}"] = [{"_id": run, "data": {"name": run}}]
    return FakeDatabaseAdapter(collections)


def _archives(db) -> list[str]:
    return sorted(
        n for n in db.list_collection_names() if n.startswith("tools_archive_")
    )


def test_prune_keeps_only_the_newest_archives():
    db = _db_with_archives(OLD_RUNS)
    repos = fake_repos(db, tools=True, tools_staging=True)

    result = finalize_run(NEW_RUN, _config(keep=2), repos)

    # This run archived the live collection, bringing the total to 5, then pruned
    # to the newest 2: this run's archive and the single newest prior one.
    surviving = _archives(db)
    assert surviving == [
        f"tools_archive_{OLD_RUNS[-1]}",
        f"tools_archive_{NEW_RUN}",
    ]
    # The 3 oldest were dropped, and finalize reported exactly them.
    assert sorted(result["pruned"]) == [f"tools_archive_{run}" for run in OLD_RUNS[:3]]


def test_pruned_run_stays_rollback_able():
    db = _db_with_archives(OLD_RUNS)
    repos = fake_repos(db, tools=True, tools_staging=True)

    finalize_run(NEW_RUN, _config(keep=2), repos)
    # The just-finalized run's archive survives pruning, so its rollback works.
    rollback_run(NEW_RUN, _config(keep=2), repos)

    assert not db.collection_exists(f"tools_archive_{NEW_RUN}"), "archive moved back"
    assert db.collection_exists("tools")


def test_keep_larger_than_the_archive_count_drops_nothing():
    db = _db_with_archives(OLD_RUNS)
    repos = fake_repos(db, tools=True, tools_staging=True)

    result = finalize_run(NEW_RUN, _config(keep=10), repos)

    assert result["pruned"] == []
    assert len(_archives(db)) == len(OLD_RUNS) + 1  # this run added one


@pytest.mark.parametrize("keep", [0, -1])
def test_keep_below_one_is_refused_and_prunes_nothing(keep):
    """keep < 1 would drop this run's own archive and break its rollback."""
    db = _db_with_archives(OLD_RUNS)
    repos = fake_repos(db, tools=True, tools_staging=True)

    result = finalize_run(NEW_RUN, _config(keep=keep), repos)

    assert result["pruned"] == []
    assert db.collection_exists(f"tools_archive_{NEW_RUN}")
    assert len(_archives(db)) == len(OLD_RUNS) + 1
