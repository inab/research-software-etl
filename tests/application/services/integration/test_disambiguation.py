"""
Disambiguation over an in-memory database.

These cases used to require a live pretoolsDev, because disambiguate_blocks()
hydrated every conflict entry through the mongo singleton. The collections are
injected now, so the pretools documents come from fixtures derived from the same
production blocks the expectations were captured against.

Two things are stubbed, and neither can change a verdict: the LLM proxy (fixed
verdict, as before) and the link enrichment, which fetches repository and webpage
content over the network. Enrichment only feeds the prompt, and the prompt's
answer is already fixed by the proxy stub.
"""

from pathlib import Path

import pytest

from application.services.integration.disambiguation.disambiguator import (
    disambiguate_blocks,
)
from application.services.integration.disambiguation.utils import load_dict_from_jsonl
from infrastructure.config import PipelineConfig
from tests.application.services.integration.data.data_disambiguation_original import (
    conflicts_blocks_sets,
    expected,
    expected_heuristics,
)
from tests.application.services.integration.pretools_fixtures import pretools_entries
from tests.fakes import FakeDatabaseAdapter, FakeGitHubClient, fake_clients, fake_repos

DATA_DIR = "tests/application/services/integration/data"

blocks = load_dict_from_jsonl(f"{DATA_DIR}/blocks.jsonl")


def config_in(tmp_path: Path, **overrides) -> PipelineConfig:
    """
    Every path the stage writes, pointed at tmp_path.

    The stage takes this config now instead of building its own, so a test no
    longer has to be insulated from it: give it a scratch config and it writes to
    scratch. `conftest.py` used to monkeypatch `PipelineConfig` inside the service
    module to stop the suite appending to tracked files in the working tree.
    """
    return PipelineConfig(
        disambiguated_blocks_path=tmp_path / "disambiguated_blocks.jsonl",
        pair_decisions_path=tmp_path / "pair_decisions.jsonl",
        proxy_results_path=tmp_path / "results_proxy.jsonl",
        conflicts_repo_dir=tmp_path / "conflicts",
        **overrides,
    )


@pytest.fixture
def repos():
    """pretools holds the four `ale` entries; publications is never reached
    (none of these entries has one), so leaving it None keeps it honest."""
    db = FakeDatabaseAdapter({"pretools": pretools_entries()})
    return fake_repos(db, pretools=True, publications=True)


@pytest.fixture
def clients():
    """Only .github is exercised -- the proxy is stubbed out, so the LLM and
    GitLab slots stay None and would blow up loudly if reached."""
    return fake_clients(github=FakeGitHubClient())


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Link enrichment reaches out to GitHub and to arbitrary webpages. Stub the
    raw fetch; the fake GitHub client covers the rest."""

    async def no_link_content(link):
        return None

    monkeypatch.setattr(
        "application.services.integration.disambiguation.enrich_links.get_link_content",
        no_link_content,
    )


def _stub_proxy(monkeypatch, verdict: str):
    def proxy(messages, clients):
        return {"verdict": verdict, "confidence": "high"}

    # NB: no "src." prefix -- the package installs as `application.*`, so
    # "src.application..." would patch a different module object and patch nothing.
    monkeypatch.setattr(
        "application.services.integration.disambiguation.disambiguator.decision_agreement_proxy",
        proxy,
    )


@pytest.mark.asyncio
async def test_real_conflict_cases(monkeypatch, tmp_path, repos, clients):
    """
    Five real conflict cases through the disambiguation pipeline. Every block in
    `blocks` is processed; those also present in the conflict set are disambiguated.

    The already-disambiguated file is truncated between cases -- a block already
    recorded there is skipped -- while the pair-decision cache is *shared* across
    them, so a decision reached in one case is reused by the next. That carry-over
    is what makes the five expected results differ.

    The original did this against a file in the repository, which left its residue
    committed; this runs in tmp_path.
    """
    _stub_proxy(monkeypatch, "different")

    config = config_in(tmp_path)
    disambiguated_path = config.disambiguated_blocks_path

    for i, conflicts_blocks in enumerate(conflicts_blocks_sets):
        disamb_result = await disambiguate_blocks(
            conflicts_blocks,
            blocks,
            config=config,
            run_id="test-run",
            clients=clients,
            repos=repos,
        )

        assert "ale/cmd" in disamb_result

        expected_result = expected[i]
        assert set(disamb_result["ale/cmd"]["merged_entries"]) == set(expected_result["merged_entries"])
        assert set(disamb_result["ale/cmd"]["unmerged_entries"]) == set(expected_result["unmerged_entries"])
        assert disamb_result["ale/cmd"]["resolution"] == expected_result["resolution"]
        assert disamb_result["ale/cmd"]["notes"] == expected_result["notes"]

        for block_id in ["1000genomes_vcf2ped/web", "mapcaller/cmd", "cvinspector/cmd"]:
            assert set(disamb_result[block_id]["merged_entries"]) == set(expected_heuristics[block_id]["merged_entries"])
            assert set(disamb_result[block_id]["unmerged_entries"]) == set(expected_heuristics[block_id]["unmerged_entries"])
            assert disamb_result[block_id]["resolution"] == expected_heuristics[block_id]["resolution"]
            assert disamb_result[block_id]["source"] == expected_heuristics[block_id]["source"]
            assert disamb_result[block_id]["notes"] == expected_heuristics[block_id]["notes"]

        # Each case starts from a clean slate of already-disambiguated blocks.
        disambiguated_path.write_text("")


@pytest.mark.asyncio
async def test_disagreement_escalates_to_a_curator(monkeypatch, tmp_path, repos, clients):
    """When the two models disagree the conflict must escalate: a conflict file is
    committed and a GitHub issue opened."""
    _stub_proxy(monkeypatch, "disagreement")

    disamb_result = await disambiguate_blocks(
        conflicts_blocks_sets[0],
        blocks,
        config=config_in(tmp_path),
        run_id="test-run",
        clients=clients,
        repos=repos,
    )

    assert "ale/cmd" in disamb_result
    assert clients.github.commits, "disagreement should commit a conflict file"
    assert clients.github.issues, "disagreement should open a GitHub issue"
    assert disamb_result["ale/cmd"]["resolution"] == "manual_review_pending"


@pytest.mark.asyncio
async def test_conflict_entries_are_hydrated_from_pretools(monkeypatch, tmp_path, repos, clients):
    """The stage reads full documents out of pretools rather than trusting the
    block: an id the collection does not hold must not silently resolve."""
    _stub_proxy(monkeypatch, "different")
    empty = fake_repos(FakeDatabaseAdapter(), pretools=True, publications=True)

    result = await disambiguate_blocks(
        conflicts_blocks_sets[0],
        blocks,
        config=config_in(tmp_path),
        run_id="test-run",
        clients=clients,
        repos=empty,
    )

    assert "ale/cmd" not in result, "an unhydratable conflict must not resolve"
