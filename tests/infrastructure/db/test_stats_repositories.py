"""
The repositories the stats and web-availability stages talk to.

None of these collections had any coverage: the code that wrote them imported the
mongo singleton, so there was no seam to put a fake behind.
"""

import pytest
from pymongo import UpdateOne

from tests.fakes import FakeDatabaseAdapter, fake_repos


@pytest.fixture
def db():
    return FakeDatabaseAdapter()


@pytest.fixture
def repos(db):
    return fake_repos(
        db, tools=True, computations=True, similarities=True, web_availability=True
    )


# --- computations -----------------------------------------------------------


def test_save_appends_a_computation(repos):
    repos.computations.save({"variable": "types_count", "data": {"cmd": 0.8}})
    repos.computations.save({"variable": "types_count", "data": {"cmd": 0.9}})

    assert len(repos.computations.find({"variable": "types_count"})) == 2, "stats append"


def test_find_by_variable_scopes_to_a_tag(repos):
    repos.computations.save({"variable": "FAIR_scores", "tags": "eucaim"})
    repos.computations.save({"variable": "FAIR_scores", "tags": "proteomics"})

    assert len(repos.computations.find_by_variable("FAIR_scores")) == 2
    assert len(repos.computations.find_by_variable("FAIR_scores", tag="eucaim")) == 1


def test_upsert_updates_rather_than_duplicating(repos):
    match = {"variable": "FAIR_scores", "createdFrom": ["tool-1"]}

    repos.computations.upsert(match, {**match, "version": "v1", "data": {"score": 1}})
    repos.computations.upsert(match, {**match, "version": "v2", "data": {"score": 2}})

    found = repos.computations.find(match)
    assert len(found) == 1, "a re-scored tool must update its document, not add one"
    assert found[0]["version"] == "v2"


# --- similarities -----------------------------------------------------------


def test_similarities_upsert_keeps_one_document_per_tool(repos):
    repos.similarities.upsert_by_tool_id({"tool_id": "t1", "similar": [{"tool_id": "t2"}]})
    repos.similarities.upsert_by_tool_id({"tool_id": "t1", "similar": [{"tool_id": "t3"}]})

    stored = repos.computations.db_adapter.fetch_entries("similarities", {})
    assert len(stored) == 1
    assert stored[0]["similar"] == [{"tool_id": "t3"}]


def test_is_empty_reflects_the_collection(repos):
    assert repos.similarities.is_empty()

    repos.similarities.upsert_by_tool_id({"tool_id": "t1"})

    assert not repos.similarities.is_empty()


def test_ensure_index_is_requested_but_never_fatal(repos, db):
    repos.similarities.ensure_tool_id_index()

    assert ("tool_id", True) in db.indexes["similarities"]


# --- web availability -------------------------------------------------------


def test_tag_relevant_creates_missing_urls_and_tags_existing_ones(repos, db):
    db.insert_one("webavailability", {"_id": "https://old.example", "data": {"availability": [1]}})

    repos.web_availability.tag_relevant(
        ["https://old.example", "https://new.example"],
        source="toolsDev",
        tagged_at="2026-07-14T00:00:00Z",
        created_by="oeb-ingest",
        updated_by="oeb-ingest",
    )

    old = db.fetch_entry("webavailability", "https://old.example")
    new = db.fetch_entry("webavailability", "https://new.example")

    assert old["relevance"]["is_relevant"] is True
    assert old["data"]["availability"] == [1], "$setOnInsert must not touch an existing doc"
    assert new["relevance"]["is_relevant"] is True
    assert new["data"]["availability"] == [], "a new url starts with no readings"


def test_append_availability_keeps_only_the_last_n_readings(repos, db):
    repos.web_availability.tag_relevant(
        ["https://x.example"],
        source="toolsDev",
        tagged_at="t0",
        created_by="a",
        updated_by="a",
    )

    for day in range(4):
        repos.web_availability.append_availability(
            [("https://x.example", {"code": 200, "day": day})],
            keep_days=3,
            updated_at="t1",
            updated_by="a",
        )

    readings = db.fetch_entry("webavailability", "https://x.example")["data"]["availability"]
    assert [r["day"] for r in readings] == [1, 2, 3], "the window rolls, oldest dropped"


def test_append_availability_never_creates_an_unmonitored_url(repos, db):
    repos.web_availability.append_availability(
        [("https://unknown.example", {"code": 200})],
        keep_days=3,
        updated_at="t",
        updated_by="a",
    )

    assert db.fetch_entry("webavailability", "https://unknown.example") is None


def test_relevant_urls_returns_only_tagged_ones(repos, db):
    db.insert_one("webavailability", {"_id": "https://untagged.example"})
    repos.web_availability.tag_relevant(
        ["https://tagged.example"],
        source="toolsDev",
        tagged_at="t",
        created_by="a",
        updated_by="a",
    )

    assert repos.web_availability.relevant_urls() == ["https://tagged.example"]


def test_existing_urls(repos, db):
    db.insert_one("webavailability", {"_id": "https://a.example"})

    found = repos.web_availability.existing_urls(
        ["https://a.example", "https://b.example"]
    )

    assert found == {"https://a.example"}


def test_the_repository_builds_the_update_operations(repos, monkeypatch):
    """The point of the repository: pymongo types never reach the application layer."""
    captured = []

    def capture(collection_name, operations, ordered=False):
        captured.extend(operations)

    monkeypatch.setattr(repos.web_availability.db_adapter, "bulk_write", capture)

    repos.web_availability.append_availability(
        [("https://x.example", {"code": 200})],
        keep_days=365,
        updated_at="t",
        updated_by="a",
    )

    assert all(isinstance(op, UpdateOne) for op in captured)
    assert captured[0]._doc["$push"]["data.availability"]["$slice"] == -365
