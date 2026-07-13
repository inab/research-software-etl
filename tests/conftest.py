"""
Keep the suite from writing into the working tree.

The disambiguation services build a ``PipelineConfig()`` inline (rather than
receiving one) and append diagnostics to paths relative to the repository root:
proxy verdicts to scripts/data/results_proxy.jsonl, plus results, issues and
error logs. Exercising them therefore modified tracked files -- which nobody
noticed while those tests were @manual and never ran.

This points those paths at tmp_path for every test. The defaults that are *read*
rather than written -- the GitHub issue template, above all -- keep their real
values, so the templates under test are the real ones.
"""

import pytest

from infrastructure.config import PipelineConfig

_REDIRECTED_MODULES = (
    "application.services.integration.disambiguation.disambiguator",
    "application.services.integration.disambiguation.issues",
)


@pytest.fixture(autouse=True)
def no_writes_to_the_working_tree(monkeypatch, tmp_path):
    scratch = tmp_path / "pipeline"
    scratch.mkdir()

    config = PipelineConfig(
        proxy_results_path=scratch / "results_proxy.jsonl",
        results_json_path=scratch / "results.json",
        issues_json_path=scratch / "issues.json",
        error_conflicts_path=scratch / "error_conflicts.json",
        conflicts_repo_dir=scratch / "conflicts",
    )

    for module in _REDIRECTED_MODULES:
        monkeypatch.setattr(f"{module}.PipelineConfig", lambda: config)

    return config
