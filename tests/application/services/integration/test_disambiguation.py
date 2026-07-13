import pytest
from application.services.integration.disambiguation.disambiguator import disambiguate_blocks
from tests.application.services.integration.data.data_disambiguation_original import conflicts_blocks_sets, expected, expected_heuristics
from application.services.integration.disambiguation.utils import load_dict_from_jsonl
from infrastructure.external.clients import ExternalClients
from pprint import pprint

DATA_DIR = 'tests/application/services/integration/data'
DISAMBIGUATED_PATH = f'{DATA_DIR}/disambiguated_blocks.jsonl'

blocks = load_dict_from_jsonl(f'{DATA_DIR}/blocks.jsonl')


class FakeGitHubClient:
    """Records issues/commits instead of touching GitHub."""

    def __init__(self):
        self.issues = []
        self.commits = []

    def commit_file(self, content, path, branch=None, repo=None):
        self.commits.append(path)
        return f"https://github.com/inab/research-software-etl/blob/main/{path}"

    def create_issue(self, title, body, labels=None, repo=None):
        self.issues.append(title)
        return {"html_url": "https://github.com/inab/research-software-etl/issues/1"}


def fake_clients():
    """Only .github is exercised here -- decision_agreement_proxy is patched out,
    so the LLM and GitLab slots stay None and would blow up loudly if reached."""
    return ExternalClients(
        openrouter=None, huggingface=None, github=FakeGitHubClient(), gitlab=None
    )


@pytest.mark.manual
@pytest.mark.asyncio
async def test_real_conflict_cases(monkeypatch, tmp_path):
    '''
    This test passes five different conflict cases to the disambiguation pipeline.
    The disambiguation runs for a set of blocks (blocks), which can be conflictive or not (if they are in conflicts_blocks or not)
    Thus, for each set of conflicts tested, all the blocks in blocks are processed and the conflictive blocks are disambiguated.

    Requires a live pretoolsDev collection: disambiguate_blocks() hydrates each
    conflict entry via replace_with_full_entries(), which calls
    mongo_adapter.fetch_entry() directly. The 11 instance ids these blocks refer
    to have no local fixtures, so this cannot run offline. Run with `pytest -m manual`.
    '''
    # --- Patch the LLM proxy so the pipeline runs without API calls ---
    def mock_decision_agreement_proxy(messages, clients):
        return {"verdict": "different", "confidence": "high"}

    monkeypatch.setattr(
        "application.services.integration.disambiguation.disambiguator.decision_agreement_proxy",
        mock_decision_agreement_proxy,
    )

    clients = fake_clients()

    # Empty decisions cache, so every pair goes through the proxy rather than
    # reusing a previously recorded decision.
    pair_decisions = tmp_path / "pair_decisions.jsonl"

    for i, conflicts_blocks in enumerate(conflicts_blocks_sets):

        disamb_result = await disambiguate_blocks(
            conflicts_blocks,
            blocks,
            disambiguated_blocks_path=DISAMBIGUATED_PATH,
            pair_wise_decisions_path=pair_decisions,
            run_id="test-run",
            clients=clients,
        )

        # --- Assertions ---

        assert "ale/cmd" in disamb_result.keys()

        print(f"------- Disambiguation result for {i} ----------------------------")
        pprint(disamb_result)

        # ---- ale/cmd conflict results -----
        expected_result = expected[i]
        assert set(disamb_result['ale/cmd']['merged_entries']) == set(expected_result['merged_entries'])
        assert set(disamb_result['ale/cmd']['unmerged_entries']) == set(expected_result['unmerged_entries'])
        assert disamb_result["ale/cmd"]["resolution"] == expected_result["resolution"]
        assert disamb_result["ale/cmd"]["notes"] == expected_result["notes"]

        # ---- other results --------
        for id in ['1000genomes_vcf2ped/web', 'mapcaller/cmd', 'cvinspector/cmd']:
            assert set(disamb_result[id]['merged_entries']) == set(expected_heuristics[id]['merged_entries'])
            assert set(disamb_result[id]['unmerged_entries']) == set(expected_heuristics[id]['unmerged_entries'])
            assert disamb_result[id]["resolution"] == expected_heuristics[id]["resolution"]
            assert disamb_result[id]["source"] == expected_heuristics[id]["source"]
            assert disamb_result[id]["notes"] == expected_heuristics[id]["notes"]

        # clean disambiguated results
        open(DISAMBIGUATED_PATH, 'w').close()

        print("===" * 20)


@pytest.mark.manual
@pytest.mark.asyncio
async def test_real_conflict_cases_human(monkeypatch, tmp_path):
    '''
    When the two models disagree, the conflict must escalate to a curator:
    a conflict file is committed and a GitHub issue is opened.

    Requires a live pretoolsDev collection (see test_real_conflict_cases).
    Run with `pytest -m manual`.
    '''
    def mock_decision_agreement_proxy(messages, clients):
        return {"verdict": "disagreement", "confidence": "high"}

    monkeypatch.setattr(
        "application.services.integration.disambiguation.disambiguator.decision_agreement_proxy",
        mock_decision_agreement_proxy,
    )

    clients = fake_clients()
    pair_decisions = tmp_path / "pair_decisions.jsonl"

    for conflicts_blocks in conflicts_blocks_sets[0:1]:

        disamb_result = await disambiguate_blocks(
            conflicts_blocks,
            blocks,
            disambiguated_blocks_path=DISAMBIGUATED_PATH,
            pair_wise_decisions_path=pair_decisions,
            run_id="test-run",
            clients=clients,
        )

        # --- Assertions ---

        assert "ale/cmd" in disamb_result.keys()

        # A disagreement must escalate: the conflict is committed and an issue opened.
        assert clients.github.commits, "disagreement should commit a conflict file"
        assert clients.github.issues, "disagreement should open a GitHub issue"
        assert disamb_result["ale/cmd"]["resolution"] == "manual_review_pending"

        open(DISAMBIGUATED_PATH, 'w').close()

