"""
The disambiguation stage end to end, over an in-memory database.

This needed a live pretoolsDev before -- disambiguate_blocks() hydrated every
conflict entry through the mongo singleton. The pretools documents are fixtures
now, derived from the same conflict blocks the test feeds in.

The LLM proxy, GitHub, and link enrichment are all faked, so this calls no model
API and opens no issue on inab/research-software-etl. Keep it that way: the
mocks used to be installed on a "src.application..." path, which does not match
the installed package name and silently patched nothing.
"""

import shutil

import pytest

from application.services.integration.disambiguation.utils import load_dict_from_jsonl
from application.use_cases.integration.disambiguation import run_full_disambiguation
from infrastructure.config import PipelineConfig
from tests.application.services.integration.pretools_fixtures import pretools_entries_for
from tests.fakes import FakeDatabaseAdapter, FakeGitHubClient, fake_clients, fake_repos

DATA_DIR = "tests/application/use_cases/integration/data"
BLOCKS_FILE = f"{DATA_DIR}/blocks.jsonl"
CONFLICT_BLOCKS_FILE = f"{DATA_DIR}/conflict_blocks.jsonl"


def config_in(tmp_path) -> PipelineConfig:
    """
    A whole run's worth of paths under tmp_path, inputs included.

    The inputs are copied rather than referenced: a second round appends its
    generated blocks back into the blocks and conflict-blocks files, so pointing
    the config straight at the checked-in fixtures would edit them in place.
    """
    blocks = tmp_path / "blocks.jsonl"
    conflicts = tmp_path / "conflict_blocks.jsonl"
    shutil.copy(BLOCKS_FILE, blocks)
    shutil.copy(CONFLICT_BLOCKS_FILE, conflicts)

    return PipelineConfig(
        grouped_json_path=blocks,
        conflicts_json_path=conflicts,
        disambiguated_blocks_path=tmp_path / "disambiguated_blocks.jsonl",
        pair_decisions_path=tmp_path / "pair_decisions.jsonl",
        proxy_results_path=tmp_path / "results_proxy.jsonl",
        conflicts_repo_dir=tmp_path / "conflicts",
    )


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Link enrichment fetches repository and webpage content; the fake GitHub
    client covers the rest."""

    async def no_link_content(link):
        return None

    monkeypatch.setattr(
        "application.services.integration.disambiguation.enrich_links.get_link_content",
        no_link_content,
    )


@pytest.mark.asyncio
async def test_full_disambiguation_with_github_issue(monkeypatch, tmp_path):
    # Force every conflict down the manual-review path.
    def mock_decision_agreement_proxy(messages, clients):
        return {"verdict": "disagreement", "confidence": "high"}

    monkeypatch.setattr(
        "application.services.integration.disambiguation.disambiguator.decision_agreement_proxy",
        mock_decision_agreement_proxy,
    )

    github = FakeGitHubClient()
    clients = fake_clients(github=github)

    conflict_blocks = load_dict_from_jsonl(CONFLICT_BLOCKS_FILE)
    db = FakeDatabaseAdapter({"pretools": pretools_entries_for(conflict_blocks)})
    repos = fake_repos(db, pretools=True, publications=True)

    # The original wrote into the data directory, leaving its output committed.
    config = config_in(tmp_path)

    await run_full_disambiguation(
        config=config,
        run_id="test-run",
        clients=clients,
        repos=repos,
        dry_run=False,
    )

    disambiguated_blocks = load_dict_from_jsonl(config.disambiguated_blocks_path)

    assert "ale/cmd" in disambiguated_blocks
    # Every conflict disagreed, so each should have escalated to a curator.
    assert github.issues
    assert github.commits


@pytest.mark.asyncio
async def test_dry_run_opens_no_issues(monkeypatch, tmp_path):
    """--dry-run-disambiguation must reach the same verdicts without escalating."""

    def mock_decision_agreement_proxy(messages, clients):
        return {"verdict": "disagreement", "confidence": "high"}

    monkeypatch.setattr(
        "application.services.integration.disambiguation.disambiguator.decision_agreement_proxy",
        mock_decision_agreement_proxy,
    )

    github = FakeGitHubClient()
    clients = fake_clients(github=github)

    conflict_blocks = load_dict_from_jsonl(CONFLICT_BLOCKS_FILE)
    db = FakeDatabaseAdapter({"pretools": pretools_entries_for(conflict_blocks)})
    repos = fake_repos(db, pretools=True, publications=True)

    await run_full_disambiguation(
        config=config_in(tmp_path),
        run_id="test-run",
        clients=clients,
        repos=repos,
        dry_run=True,
    )

    assert not github.issues, "a dry run must not open GitHub issues"
    assert not github.commits, "a dry run must not commit conflict files"
