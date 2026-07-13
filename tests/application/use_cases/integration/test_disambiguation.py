from application.use_cases.integration.disambiguation import run_full_disambiguation
from application.services.integration.disambiguation.utils import load_dict_from_jsonl
from infrastructure.external.clients import ExternalClients
import pytest


# Manual: needs a live pretoolsDev collection (disambiguate_blocks hydrates each
# conflict entry from Mongo). Run with `pytest -m manual`.
#
# The LLM proxy and GitHub are both faked below, so this does NOT call the model
# APIs and does NOT open issues on inab/research-software-etl. Keep it that way:
# the mocks used to be installed on a "src.application..." path, which does not
# match the installed package name and silently patched nothing.


class FakeGitHubClient:
    def __init__(self):
        self.issues = []
        self.commits = []

    def commit_file(self, content, path, branch=None, repo=None):
        self.commits.append(path)
        return f"https://github.com/inab/research-software-etl/blob/main/{path}"

    def create_issue(self, title, body, labels=None, repo=None):
        self.issues.append(title)
        return {"html_url": f"https://github.com/inab/research-software-etl/issues/{len(self.issues)}"}


@pytest.mark.manual
@pytest.mark.asyncio
async def test_full_disambiguation_with_github_issue(monkeypatch, tmp_path):
    data_dir = 'tests/application/use_cases/integration/data'
    blocks_file = f'{data_dir}/blocks.jsonl'
    conflict_blocks_file = f'{data_dir}/conflict_blocks.jsonl'
    disambiguated_blocks_file = f'{data_dir}/disambiguated_blocks.jsonl'

    # Force every conflict down the manual-review path.
    def mock_decision_agreement_proxy(messages, clients):
        return {"verdict": "disagreement", "confidence": "high"}

    monkeypatch.setattr(
        "application.services.integration.disambiguation.disambiguator.decision_agreement_proxy",
        mock_decision_agreement_proxy,
    )

    github = FakeGitHubClient()
    clients = ExternalClients(
        openrouter=None, huggingface=None, github=github, gitlab=None
    )

    await run_full_disambiguation(
        blocks_file=blocks_file,
        conflict_blocks_file=conflict_blocks_file,
        disambiguated_blocks_file=disambiguated_blocks_file,
        pair_wise_decisions_file=tmp_path / "pair_decisions.jsonl",
        run_id="test-run",
        clients=clients,
        dry_run=False,
    )

    disambiguated_blocks = load_dict_from_jsonl(disambiguated_blocks_file)

    assert "ale/cmd" in disambiguated_blocks.keys()
    # Every conflict disagreed, so each should have escalated to a curator.
    assert github.issues
    assert github.commits
