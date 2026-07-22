"""
The web-availability stage over an in-memory database.

It had no coverage at all: it imported the mongo singleton and built
`pymongo.UpdateOne` objects by hand, so there was nowhere to put a fake and no way
to assert what it wrote without a live MongoDB. Both are gone -- the use cases pass
plain data to `WebAvailabilityRepository`, which owns the driver types -- and these
tests pin the behaviour that migration had to preserve.
"""

import pytest

from application.use_cases.web_availability.tag_relevant_webavailability_urls import (
    TagRelevantWebAvailabilityConfig,
    run_tag_relevant_webavailability_urls,
)
from application.use_cases.web_availability.update_web_availability import (
    WebAvailabilityConfig,
    run_update_web_availability,
)
from tests.fakes import FakeDatabaseAdapter, FakeUrlChecker, fake_repos


def tool(identifier, types, webpages):
    return {"_id": identifier, "data": {"type": types, "webpage": webpages}}


def monitored(url, availability=None):
    """A web-availability document already flagged relevant."""
    return {
        "_id": url,
        "is_relevant": True,
        "data": {"url": url, "availability": availability or []},
    }


@pytest.fixture
def checker():
    """
    Every URL answers 200 in 0.1s, without touching the network.

    The stage used to build its own `requests.Session`, so this was a monkeypatch
    of a module global. It is an argument now.
    """
    return FakeUrlChecker()


def build(db):
    return fake_repos(db, tools=True, web_availability=True)


# --- step 1: check the URLs already flagged relevant --------------------------------


def test_appends_one_reading_per_relevant_url(checker):
    db = FakeDatabaseAdapter(
        {
            "webavailability": [
                monitored("https://a.org"),
                # Not flagged relevant: the imported collection carries URLs that are
                # not tool webpages, and the job must leave them alone.
                {"_id": "https://ignored.org", "data": {"availability": []}},
            ],
            "tools": [],
        }
    )
    repos = build(db)

    result = run_update_web_availability(WebAvailabilityConfig(), repos, checker)

    assert result.processed_existing_urls == 1

    checked = db.fetch_entry("webavailability", "https://a.org")
    assert [r["code"] for r in checked["data"]["availability"]] == [200]
    assert checked["last_updated_at"] == checked["data"]["availability"][0]["date"]

    untouched = db.fetch_entry("webavailability", "https://ignored.org")
    assert untouched["data"]["availability"] == []


def test_keeps_only_the_last_keep_days_readings(checker):
    old = [{"date": f"2026-0{n}-01T00:00:00Z", "code": 200, "access_time": 0.1} for n in (1, 2, 3)]
    db = FakeDatabaseAdapter({"webavailability": [monitored("https://a.org", old)], "tools": []})

    run_update_web_availability(
        WebAvailabilityConfig(keep_days=2), repos=build(db), url_checker=checker
    )

    window = db.fetch_entry("webavailability", "https://a.org")["data"]["availability"]
    assert len(window) == 2
    assert window[0]["date"] == "2026-03-01T00:00:00Z"  # the oldest two rolled off


def test_rejects_a_window_of_nothing():
    with pytest.raises(ValueError):
        run_update_web_availability(
            WebAvailabilityConfig(keep_days=0),
            repos=build(FakeDatabaseAdapter()),
            url_checker=FakeUrlChecker(),
        )


# --- step 2: make sure relevant tool URLs are tracked -------------------------------


def test_tracks_the_webpages_of_relevant_tools(checker):
    db = FakeDatabaseAdapter(
        {
            "webavailability": [],
            "tools": [
                tool("t1", ["web"], ["https://new.org"]),
                # A command-line tool has no webpage worth monitoring.
                tool("t2", ["cmd"], ["https://cmd.org"]),
            ],
        }
    )
    repos = build(db)

    result = run_update_web_availability(WebAvailabilityConfig(), repos, checker)

    assert result.tools_unique_urls == 1
    assert result.inserted_missing_urls == 1

    created = db.fetch_entry("webavailability", "https://new.org")
    assert created["is_relevant"] is True
    assert created["relevance"]["source"] == "tools"
    assert created["data"]["availability"] == []

    assert db.fetch_entry("webavailability", "https://cmd.org") is None


def test_flags_a_url_an_earlier_process_created(checker):
    """
    The collection was seeded from a broader dataset. A URL already sitting there
    unflagged must get tagged -- otherwise step 1 never picks it up and it is
    monitored by nobody.
    """
    stale = {"_id": "https://old.org", "data": {"url": "https://old.org", "availability": []}}
    db = FakeDatabaseAdapter(
        {"webavailability": [stale], "tools": [tool("t1", ["rest"], ["https://old.org"])]}
    )
    repos = build(db)

    result = run_update_web_availability(WebAvailabilityConfig(), repos, checker)

    assert (result.retagged_existing_urls, result.inserted_missing_urls) == (1, 0)
    assert db.fetch_entry("webavailability", "https://old.org")["is_relevant"] is True


def test_dry_run_writes_nothing(checker):
    db = FakeDatabaseAdapter(
        {
            "webavailability": [monitored("https://a.org")],
            "tools": [tool("t1", ["web"], ["https://new.org"])],
        }
    )

    result = run_update_web_availability(
        WebAvailabilityConfig(dry_run=True), repos=build(db), url_checker=checker
    )

    assert result.processed_existing_urls == 1  # it still reports what it *would* do
    assert db.fetch_entry("webavailability", "https://a.org")["data"]["availability"] == []
    assert db.fetch_entry("webavailability", "https://new.org") is None


# --- the one-shot tagging backfill --------------------------------------------------


def test_tagging_upserts_every_relevant_tool_url():
    db = FakeDatabaseAdapter(
        {
            "webavailability": [],
            "tools": [
                tool("t1", ["web", "cmd"], ["https://a.org"]),
                tool("t2", ["db"], ["https://b.org", "not-a-url"]),
                tool("t3", ["cmd"], ["https://c.org"]),
                tool("t4", ["web"], "https://not-a-list.org"),
            ],
        }
    )

    result = run_tag_relevant_webavailability_urls(
        TagRelevantWebAvailabilityConfig(), repos=build(db)
    )

    assert result.tools_scanned == 4
    assert result.tools_matched == 3  # t4 matches on type, and contributes no URL
    assert result.relevant_urls_found == 2
    assert result.upserts_sent == 2

    tagged = db.fetch_entries("webavailability", {"is_relevant": True})
    assert sorted(d["_id"] for d in tagged) == ["https://a.org", "https://b.org"]
    assert all(d["data"]["availability"] == [] for d in tagged)
    assert all(d["created_logs"] == "tag-relevant-urls" for d in tagged)


def test_tagging_batches_do_not_lose_urls():
    """A URL set larger than one bulk chunk must still be written whole."""
    tools = [tool(f"t{n}", ["web"], [f"https://{n}.org"]) for n in range(7)]
    db = FakeDatabaseAdapter({"webavailability": [], "tools": tools})

    result = run_tag_relevant_webavailability_urls(
        TagRelevantWebAvailabilityConfig(bulk_chunk=2), repos=build(db)
    )

    assert result.upserts_sent == 7
    assert len(db.fetch_entries("webavailability", {"is_relevant": True})) == 7
