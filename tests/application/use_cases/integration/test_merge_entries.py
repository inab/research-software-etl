"""
Merging used to be untestable offline: it fetched every entry id straight from
a live pretoolsDev via the mongo singleton, and the test had to patch save_entry
out to avoid inserting real documents into the tools collection. Both
collections are injected now, so the whole stage runs against an in-memory
database and the writes can be *asserted* rather than suppressed.
"""

import json

import pytest

from application.use_cases.integration.merge_entries import (
    fetch_entry_from_db,
    merge_and_save_blocks,
)
from tests.fakes import FakeDatabaseAdapter, fake_repos

BLOCKS_FILE = "tests/application/use_cases/integration/data/disambiguated_blocks_2.jsonl"


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


def _entry_ids_in(blocks_file: str) -> set[str]:
    ids: set[str] = set()
    with open(blocks_file) as handle:
        for line in handle:
            if not line.strip():
                continue
            for block in json.loads(line).values():
                for group in ("merged_entries", "unmerged_entries"):
                    ids.update(block.get(group) or [])
    return ids


@pytest.fixture
def repos():
    db = FakeDatabaseAdapter(
        {"pretools": [_pretools_entry(i) for i in _entry_ids_in(BLOCKS_FILE)]}
    )
    return fake_repos(db, pretools=True, tools=True, tools_staging=True)


def test_merge_and_save_blocks(repos):
    summary = merge_and_save_blocks(BLOCKS_FILE, repos)

    assert summary["N"] == 6
    assert summary["n_processed"] == 4
    assert summary["n_inserted_entries"] == 5
    assert summary["n_pending"] == 1
    assert summary["n_unclear"] == 1


def test_merged_entries_are_written_to_the_staging_collection(repos):
    merge_and_save_blocks(BLOCKS_FILE, repos)

    written = repos.tools_staging.get_all()

    assert repos.tools.get_all() == [], "the live collection is untouched until promotion"
    assert len(written) == 5, "one document per inserted entry"
    # Unresolved blocks (manual_review_pending, unclear) must not reach tools.
    names = {entry["data"]["name"] for entry in written}
    assert "ale" not in names


def test_a_merged_entry_records_the_ids_it_came_from(repos):
    merge_and_save_blocks(BLOCKS_FILE, repos)

    single = next(
        entry
        for entry in repos.tools_staging.get_all()
        if entry["data"]["name"] == "1000genomes_vcf2ped"
    )

    assert single["source"] == ["biotools/1000genomes_vcf2ped/web/1"]
    assert single["data"]["type"] == ["web"]


def test_fetch_entry_from_db(repos):
    entry = fetch_entry_from_db("bioconda_recipes/ale/cmd/20180904", repos)

    assert entry is not None
    assert entry["_id"] == "bioconda_recipes/ale/cmd/20180904"
    assert "data" in entry


def test_fetch_entry_from_db_returns_none_when_absent(repos):
    assert fetch_entry_from_db("nope/nope/cmd/1", repos) is None
