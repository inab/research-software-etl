"""Focused unit tests for the two services `process_conflict` was split into.

`PairScoringService` is the LLM side and must run with no GitHub in sight;
`DisambiguationReviewService` is the cache + GitHub side and must run with no LLM
in sight. Together they pin the split in `disambiguator.py`.
"""

import pytest

from application.services.integration.disambiguation.pair_scoring import PairScoringService
from application.services.integration.disambiguation.review import DisambiguationReviewService
from application.services.integration.disambiguation.utils import replace_with_full_entries
from infrastructure.config import PipelineConfig
from tests.application.services.integration.data.data_disambiguation_original import (
    conflicts_blocks_sets,
)
from tests.application.services.integration.pretools_fixtures import pretools_entries
from tests.fakes import FakeDatabaseAdapter, FakeGitHubClient, fake_clients, fake_repos


@pytest.fixture
def repos():
    db = FakeDatabaseAdapter({"pretools": pretools_entries()})
    return fake_repos(db, pretools=True, publications=True)


@pytest.fixture
def clients():
    """Only the tokenless fetchers (offline fakes) and github are filled; the LLM
    slots stay None so a stray proxy call would blow up loudly."""
    return fake_clients(github=FakeGitHubClient())


@pytest.mark.asyncio
async def test_pair_scoring_scores_without_touching_github(monkeypatch, tmp_path, repos, clients):
    def proxy(messages, clients):
        return {"verdict": "different", "confidence": "high"}

    # No "src." prefix -- the package installs as `application.*`.
    monkeypatch.setattr(
        "application.services.integration.disambiguation.pair_scoring.decision_agreement_proxy",
        proxy,
    )

    proxy_path = tmp_path / "results_proxy.jsonl"
    scoring = PairScoringService(clients, repos, proxy_path)

    conflict = conflicts_blocks_sets[0]["ale/cmd"]
    conflict_full = replace_with_full_entries(conflict, repos.pretools)
    pairs = scoring.build_pairs(conflict_full, "ale/cmd")
    assert pairs, "expected at least one pair from a 1-disconnected / 2-remaining block"

    scored = await scoring.score(pairs[0], "ale/cmd")

    assert scored.result["verdict"] == "different"
    assert "disconnected" in scored.full_conflict and "remaining" in scored.full_conflict
    # The run-scoped proxy diagnostic was written...
    assert proxy_path.exists()
    # ...and no GitHub side effects happened during scoring.
    assert not clients.github.issues
    assert not clients.github.commits


def _minimal_entry(entry_id):
    """The smallest shape `preprocess_entry` accepts: a non-empty `source` list and
    an iterable `repository`; every other field tolerates None."""
    return {
        "id": entry_id,
        "name": entry_id,
        "source": ["biotools"],
        "repository": [],
        "webpage": None,
        "authors": None,
        "publications": None,
        "license": None,
        "description": None,
        "documentation": None,
    }


def _review(tmp_path, clients, dry_run=False):
    config = PipelineConfig(
        pair_decisions_path=tmp_path / "pair_decisions.jsonl",
        conflicts_repo_dir=tmp_path / "conflicts",
    )
    return DisambiguationReviewService(clients, config, {}, run_id="test-run", dry_run=dry_run), config


def test_review_records_decision_into_cache(tmp_path, clients):
    review, config = _review(tmp_path, clients)

    assert review.cached("p:demo") is None
    payload = review.record("p:demo", {"verdict": "Same", "confidence": "high"})

    assert payload["decision"] == "same"
    assert payload["same_as_remaining"] is True
    assert payload["source"] == "llm"
    # In-memory cache and the persisted history both updated.
    assert review.cached("p:demo") == payload
    assert config.pair_decisions_path.exists()


def test_review_opens_issue_without_touching_llm(tmp_path, clients):
    review, _ = _review(tmp_path, clients)

    conflict = {"remaining": [{"id": "r"}], "disconnected": [{"id": "d"}]}
    conflict_pair = {"remaining": [{"_id": "r"}], "disconnected": [{"_id": "d"}]}
    full_conflict = {"disconnected": [_minimal_entry("d")], "remaining": [_minimal_entry("r")]}

    issue_url, dry_run_record = review.open_issue(
        conflict, conflict_pair, "ale/cmd", "p:demo", full_conflict, 1
    )

    assert dry_run_record is None
    assert issue_url  # the FakeGitHubClient's issue URL
    assert clients.github.issues  # one issue opened
    assert clients.github.commits  # conflict file committed
    # The LLM slots were never needed.
    assert clients.openrouter is None
    assert clients.huggingface is None


def test_review_dry_run_opens_nothing(tmp_path, clients):
    review, _ = _review(tmp_path, clients, dry_run=True)

    conflict = {"remaining": [{"id": "r"}], "disconnected": [{"id": "d"}]}
    conflict_pair = {"remaining": [{"_id": "r"}], "disconnected": [{"_id": "d"}]}
    full_conflict = {"disconnected": [_minimal_entry("d")], "remaining": [_minimal_entry("r")]}

    issue_url, dry_run_record = review.open_issue(
        conflict, conflict_pair, "ale/cmd", "p:demo", full_conflict, 1
    )

    assert issue_url is None
    assert dry_run_record["would_create_issue"] is True
    assert dry_run_record["resolution"] == "manual_review_pending"
    assert dry_run_record["pair_id"] == "p:demo"
    # Nothing reached GitHub.
    assert not clients.github.issues
    assert not clients.github.commits
