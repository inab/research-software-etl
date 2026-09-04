"""
Merge -> promote -> merge again, on an in-memory database.

The feature in one sentence: run the pipeline twice and a tool keeps its `_id`.
Everything downstream depends on that -- FAIR scores upsert on
`computationsDev.createdFrom = [str(tool._id)]`, and the front-end looks tools up
by `similaritiesDev.tool_id`.

These use a purpose-built blocks file rather than the shared
`disambiguated_blocks_2.jsonl`, which contains two blocks with identical source
lists (`mapcaller/cmd` and `mapcall/cmd`) -- fine for testing merge, but it makes
"which tool is this?" ambiguous when the point is to track a tool across runs.
"""

import json

import pytest

from application.use_cases.integration.finalize_run import (
    FinalizeRunError,
    finalize_run,
    rollback_run,
)
from application.use_cases.integration.merge_entries import merge_and_save_blocks
from infrastructure.config import PipelineConfig
from tests.fakes import FakeDatabaseAdapter, fake_repos

ABYSS = "bioconda_recipes/abyss/cmd/2.0"
ABYSS_BIOTOOLS = "biotools/abyss/cmd/None"
ABYSS_V3 = "bioconda_recipes/abyss/cmd/3.0"
SPADES = "bioconda_recipes/spades/cmd/3.15"
VELVET = "biotools/velvet/cmd/None"


def blocks(tmp_path, spec: dict) -> str:
    """Write a disambiguated-blocks file: {block_key: [pretools ids]}."""
    path = tmp_path / "blocks.jsonl"
    with path.open("w") as handle:
        for key, entry_ids in spec.items():
            handle.write(
                json.dumps(
                    {
                        key: {
                            "resolution": "no_conflict",
                            "merged_entries": list(entry_ids),
                            "unmerged_entries": [],
                        }
                    }
                )
                + "\n"
            )
    return str(path)


def _pretools_entry(entry_id: str) -> dict:
    source, name, type_, version = entry_id.split("/")
    return {
        "_id": entry_id,
        "data": {
            "name": name,
            "type": None if type_ == "None" else type_,
            "version": [] if version == "None" else [version],
            "source": [source],
        },
    }


@pytest.fixture
def config():
    return PipelineConfig(
        tools_collection="tools",
        tools_staging_collection="tools_next",
        tools_archive_prefix="tools_archive_",
    )


@pytest.fixture
def db():
    return FakeDatabaseAdapter(
        {
            "pretools": [
                _pretools_entry(i)
                for i in (ABYSS, ABYSS_BIOTOOLS, ABYSS_V3, SPADES, VELVET)
            ]
        }
    )


@pytest.fixture
def repos(db):
    return fake_repos(db, pretools=True, tools=True, tools_staging=True)


@pytest.fixture
def first_run(tmp_path, repos, config):
    """Two tools: abyss (two sources) and spades (one)."""
    spec = {"abyss/cmd": [ABYSS, ABYSS_BIOTOOLS], "spades/cmd": [SPADES]}
    merge_and_save_blocks(blocks(tmp_path, spec), repos)
    finalize_run("run-1", config, repos)
    return ids_by_name(repos)


def ids_by_name(repos) -> dict:
    return {entry["data"]["name"]: entry["_id"] for entry in repos.tools.get_all()}


def timestamps_by_name(repos) -> dict:
    return {entry["data"]["name"]: entry["last_updated_at"] for entry in repos.tools.get_all()}


def merge_and_promote(tmp_path, repos, config, spec, run_id):
    summary = merge_and_save_blocks(blocks(tmp_path, spec), repos)
    finalize_run(run_id, config, repos)
    return summary


def test_an_unchanged_run_preserves_every_id(tmp_path, repos, config, first_run):
    summary = merge_and_promote(
        tmp_path,
        repos,
        config,
        {"abyss/cmd": [ABYSS, ABYSS_BIOTOOLS], "spades/cmd": [SPADES]},
        "run-2",
    )

    assert ids_by_name(repos) == first_run
    assert summary["identities"] == {"preserved": 2, "new": 0, "retired": 0, "contested": 0}


def test_an_unchanged_tool_keeps_its_timestamp(tmp_path, repos, config, first_run):
    """
    A tool whose content did not change keeps the previous run's timestamp, so the
    FAIR stage -- which skips when the stored score's version matches the tool
    timestamp -- does not recompute it. This is the whole point of hashing content.
    """
    before = timestamps_by_name(repos)

    merge_and_promote(
        tmp_path,
        repos,
        config,
        {"abyss/cmd": [ABYSS, ABYSS_BIOTOOLS], "spades/cmd": [SPADES]},
        "run-2",
    )

    assert timestamps_by_name(repos) == before, "no content change, no new timestamp"


def test_a_changed_tool_bumps_its_timestamp(tmp_path, repos, config, first_run):
    """Adding a release changes abyss's merged content, so its timestamp moves;
    spades is untouched and keeps its timestamp."""
    before = timestamps_by_name(repos)

    merge_and_promote(
        tmp_path,
        repos,
        config,
        {"abyss/cmd": [ABYSS, ABYSS_BIOTOOLS, ABYSS_V3], "spades/cmd": [SPADES]},
        "run-2",
    )

    after = timestamps_by_name(repos)
    assert after["abyss"] > before["abyss"], "changed content gets a fresh timestamp"
    assert after["spades"] == before["spades"], "unchanged tool keeps its timestamp"


def test_an_id_survives_a_new_release_joining_its_group(tmp_path, repos, config, first_run):
    """The common case: bioconda ships abyss 3.0, so a new pretools id appears."""
    summary = merge_and_promote(
        tmp_path,
        repos,
        config,
        {"abyss/cmd": [ABYSS, ABYSS_BIOTOOLS, ABYSS_V3], "spades/cmd": [SPADES]},
        "run-2",
    )

    assert ids_by_name(repos)["abyss"] == first_run["abyss"]
    assert summary["identities"]["preserved"] == 2
    grown = next(e for e in repos.tools.get_all() if e["data"]["name"] == "abyss")
    assert ABYSS_V3 in grown["source"]


def test_an_id_survives_an_entry_being_removed_from_its_group(
    tmp_path, repos, config, first_run
):
    """A cleanup script deleted a pretools entry. Strict superset would churn here."""
    summary = merge_and_promote(
        tmp_path, repos, config, {"abyss/cmd": [ABYSS], "spades/cmd": [SPADES]}, "run-2"
    )

    assert ids_by_name(repos)["abyss"] == first_run["abyss"]
    assert summary["identities"]["preserved"] == 2


def test_a_brand_new_tool_gets_a_fresh_id(tmp_path, repos, config, first_run):
    summary = merge_and_promote(
        tmp_path,
        repos,
        config,
        {
            "abyss/cmd": [ABYSS, ABYSS_BIOTOOLS],
            "spades/cmd": [SPADES],
            "velvet/cmd": [VELVET],
        },
        "run-2",
    )

    ids = ids_by_name(repos)
    assert ids["abyss"] == first_run["abyss"]
    assert ids["velvet"] not in first_run.values()
    assert summary["identities"] == {"preserved": 2, "new": 1, "retired": 0, "contested": 0}


def test_a_tool_that_disappears_retires_its_id(tmp_path, repos, config, first_run):
    summary = merge_and_promote(
        tmp_path, repos, config, {"abyss/cmd": [ABYSS, ABYSS_BIOTOOLS]}, "run-2"
    )

    assert "spades" not in ids_by_name(repos)
    assert summary["identities"] == {"preserved": 1, "new": 0, "retired": 1, "contested": 0}


def test_created_at_is_set_once_and_carried_forward(tmp_path, repos, config, first_run):
    original = {e["_id"]: e["created_at"] for e in repos.tools.get_all()}

    merge_and_promote(
        tmp_path,
        repos,
        config,
        {"abyss/cmd": [ABYSS, ABYSS_BIOTOOLS, ABYSS_V3], "spades/cmd": [SPADES]},
        "run-2",
    )

    for entry in repos.tools.get_all():
        assert entry["created_at"] == original[entry["_id"]], "created_at is never rewritten"
        assert entry["last_updated_at"] >= entry["created_at"], "update time tracks the latest run"


def test_promotion_archives_the_collection_it_replaces(tmp_path, repos, db, config, first_run):
    merge_and_promote(
        tmp_path,
        repos,
        config,
        {"abyss/cmd": [ABYSS, ABYSS_BIOTOOLS], "spades/cmd": [SPADES]},
        "run-2",
    )

    assert db.collection_exists("tools_archive_run-2")
    assert not db.collection_exists("tools_next"), "staging is consumed by the promotion"
    archived = repos.tools.for_collection("tools_archive_run-2").get_all()
    assert {e["data"]["name"]: e["_id"] for e in archived} == first_run


def test_the_live_collection_is_untouched_until_promotion(tmp_path, repos, config, first_run):
    merge_and_save_blocks(
        blocks(tmp_path, {"abyss/cmd": [ABYSS, ABYSS_BIOTOOLS, ABYSS_V3]}), repos
    )

    assert ids_by_name(repos) == first_run, "still serving the previous run's tools"
    assert len(repos.tools_staging.get_all()) == 1


def test_rollback_restores_the_archived_collection(tmp_path, repos, db, config, first_run):
    merge_and_promote(tmp_path, repos, config, {"abyss/cmd": [ABYSS]}, "run-2")
    assert "spades" not in ids_by_name(repos), "run-2 dropped spades"

    rollback_run("run-2", config, repos)

    assert ids_by_name(repos) == first_run, "run-1's tools are back, ids and all"
    assert not db.collection_exists("tools_archive_run-2"), "the archive was moved back"


def test_rollback_without_an_archive_is_refused(repos, config):
    with pytest.raises(FinalizeRunError, match="no archive"):
        rollback_run("never-ran", config, repos)


def test_finalizing_without_a_merge_is_refused(repos, config):
    with pytest.raises(FinalizeRunError, match="nothing to promote"):
        finalize_run("run-1", config, repos)


def test_stale_staging_from_a_failed_run_is_not_promoted(tmp_path, repos, config, first_run):
    """A crashed run can leave documents in staging. They are not this run's output."""
    repos.tools_staging.insert(
        {"_id": "leftover", "source": ["x"], "data": {"name": "leftover"}}
    )

    merge_and_promote(tmp_path, repos, config, {"abyss/cmd": [ABYSS]}, "run-2")

    assert "leftover" not in ids_by_name(repos)
