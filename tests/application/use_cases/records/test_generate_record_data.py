"""
The per-record orchestrator (`rsetl enrich-tool`) over fake repositories.

It ties together three services that each have their own tests; here we pin that
one call refreshes all three collections for a single tool, offline. The heavy
FAIR scorer is patched at its real module path (never `src.`-prefixed, which
would patch nothing) -- everything else runs for real against in-memory fakes.
"""

import numpy as np
import pytest

from application.use_cases.records.generate_record_data import generate_record_data
from application.use_cases.web_availability.update_web_availability import (
    WebAvailabilityConfig,
)
from tests.fakes import FakeDatabaseAdapter, FakeUrlChecker, fake_repos


TOOL = {
    "_id": "tgt",
    "timestamp": "2026-08-21T00:00:00Z",
    "data": {
        "name": "Target",
        "type": ["web"],
        "webpage": ["https://target.org"],
        "tags": [],
    },
}


def _repos(db):
    return fake_repos(
        db,
        tools=True,
        publications=True,
        computations=True,
        similarities=True,
        embeddings=True,
        web_availability=True,
    )


def _seed(repos):
    # A corpus of one so similarity has something to compare against.
    repos.embeddings.upsert_by_tool_id(
        tool_id="c1",
        tool_name="C1",
        text="C1",
        vector=[1.0, 0.0],
        model="m",
        version="v1",
    )


def make_embedder():
    return lambda text: np.array([1.0, 0.0], dtype=np.float32)


def test_enrich_tool_refreshes_all_three(monkeypatch):
    monkeypatch.setattr(
        "application.use_cases.stats.generate_fair_scores.evaluate_tool",
        lambda entry, publications: {"F": 1.0, "A": 1.0, "I": 1.0, "R": 1.0},
    )

    db = FakeDatabaseAdapter({"tools": [TOOL]})
    repos = _repos(db)
    _seed(repos)

    result = generate_record_data(
        repos,
        tool_id="tgt",
        url_checker=FakeUrlChecker(),
        make_embedder=make_embedder,
        model_name="m",
        k=2,
    )

    assert result["ok"] is True
    assert result["failed_stages"] == []
    assert result["fair"]["status"] == "processed"
    assert result["web_availability"]["urls"] == ["https://target.org"]
    assert result["similarity"]["neighbours"] == 1

    # FAIR score stored, keyed on the tool id.
    fair = db.fetch_entry("computations", {"createdFrom": ["tgt"]})
    assert fair["variable"] == "FAIR_scores"
    assert fair["data"]["F"] == 1.0

    # The tool's webpage got a document and a reading.
    web = db.fetch_entry("webavailability", "https://target.org")
    assert web["is_relevant"] is True
    assert [r["code"] for r in web["data"]["availability"]] == [200]

    # Similarity neighbours and the fresh embedding are stored.
    assert repos.similarities.find_by_tool_id("tgt")["similar"][0]["tool_id"] == "c1"
    assert repos.embeddings.get("tgt") is not None


def test_similarity_failure_does_not_block_fair_and_web(monkeypatch):
    """An empty embedding cache must not sink the stages that can run."""
    monkeypatch.setattr(
        "application.use_cases.stats.generate_fair_scores.evaluate_tool",
        lambda entry, publications: {"F": 1.0},
    )

    db = FakeDatabaseAdapter({"tools": [TOOL]})
    repos = _repos(db)
    # No embeddings seeded: compute_record_similarity raises "cache is empty".

    result = generate_record_data(
        repos,
        tool_id="tgt",
        url_checker=FakeUrlChecker(),
        make_embedder=make_embedder,
        model_name="m",
        k=2,
    )

    assert result["ok"] is False
    assert result["failed_stages"] == ["similarity"]
    assert "error" in result["similarity"]

    # FAIR and web still ran and persisted.
    assert result["fair"]["status"] == "processed"
    assert db.fetch_entry("computations", {"createdFrom": ["tgt"]}) is not None
    web = db.fetch_entry("webavailability", "https://target.org")
    assert [r["code"] for r in web["data"]["availability"]] == [200]


def test_missing_tool_raises(monkeypatch):
    db = FakeDatabaseAdapter({"tools": []})
    repos = _repos(db)

    with pytest.raises(ValueError, match="No tool found"):
        generate_record_data(
            repos,
            tool_id="nope",
            url_checker=FakeUrlChecker(),
            make_embedder=make_embedder,
            model_name="m",
        )


def test_dry_run_probes_but_writes_no_web_availability(monkeypatch):
    monkeypatch.setattr(
        "application.use_cases.stats.generate_fair_scores.evaluate_tool",
        lambda entry, publications: {"F": 1.0},
    )
    db = FakeDatabaseAdapter({"tools": [TOOL]})
    repos = _repos(db)
    _seed(repos)

    result = generate_record_data(
        repos,
        tool_id="tgt",
        url_checker=FakeUrlChecker(),
        make_embedder=make_embedder,
        model_name="m",
        k=2,
        wa_config=WebAvailabilityConfig(dry_run=True),
    )

    assert result["web_availability"]["probed"] == 1
    assert db.fetch_entry("webavailability", "https://target.org") is None
