"""
FAIR distributions. Untestable before -- the module imported the mongo singleton.

Two of these pin bugs the singleton was hiding: the dedup that raised TypeError on
every call, and a tools query that could never match anything.
"""

import pytest

from application.services.stats_generation.FAIR.fair_distribution import (
    compute_fair_distributions,
    do_sanity_check,
    get_fair_scores,
)
from tests.fakes import FakeDatabaseAdapter, fake_repos


def fair_score(tool_id, version, score=1.0, tags=None):
    return {
        "variable": "FAIR_scores",
        "createdFrom": [tool_id],  # a one-element LIST, since db_createdFrom_to_list.py
        "version": version,
        "tags": tags if tags is not None else [],
        "data": {"F": score, "F1": score, "F2": score, "F3": score,
                 "A": score, "A1": score, "A3": score,
                 "I": score, "I1": score, "I2": score, "I3": score,
                 "R": score, "R1": score, "R2": score, "R3": score, "R4": score},
    }


@pytest.fixture
def db():
    return FakeDatabaseAdapter()


@pytest.fixture
def repos(db):
    return fake_repos(db, tools=True, computations=True)


def test_the_latest_score_per_tool_wins(repos):
    """
    Regression: this keyed a dict on `createdFrom`, which is a *list* and therefore
    unhashable, so it raised `TypeError: unhashable type: 'list'` -- the dedup had
    not run since createdFrom was migrated to a list.
    """
    repos.computations.save(fair_score("tool-1", "2026-01-01T00:00:00", score=0.2))
    repos.computations.save(fair_score("tool-1", "2026-06-01T00:00:00", score=0.9))
    repos.computations.save(fair_score("tool-2", "2026-03-01T00:00:00", score=0.5))

    results = get_fair_scores("tools", repos.computations)

    assert len(results) == 2, "one score per tool, the most recent"
    by_tool = {r["createdFrom"][0]: r["data"]["F"] for r in results}
    assert by_tool == {"tool-1": 0.9, "tool-2": 0.5}


def test_scores_can_be_scoped_to_a_tag(repos):
    repos.computations.save(fair_score("tool-1", "2026-01-01T00:00:00", tags="eucaim"))
    repos.computations.save(fair_score("tool-2", "2026-01-01T00:00:00", tags="proteomics"))

    assert len(get_fair_scores("tools", repos.computations)) == 2
    assert len(get_fair_scores("eucaim", repos.computations)) == 1


def test_entries_without_a_version_are_ignored(repos):
    repos.computations.save({"variable": "FAIR_scores", "createdFrom": ["t"], "data": {}})

    assert get_fair_scores("tools", repos.computations) == []


def test_the_sanity_check_finds_tag_scoped_tools(repos, capsys):
    """
    Regression: tools carry their tags at `data.tags`, but this queried a top-level
    `tags` field that does not exist on a tool -- so it always counted zero tools and
    warned about a mismatch that was not real.
    """
    repos.tools.insert({"_id": "t1", "data": {"name": "x", "tags": ["eucaim"]}})
    repos.computations.save(fair_score("t1", "2026-01-01T00:00:00", tags="eucaim"))

    do_sanity_check("eucaim", repos)

    assert "Same number of tools and FAIR score records" in capsys.readouterr().out


def test_distributions_are_written_for_the_collection(repos):
    for i in range(3):
        repos.computations.save(fair_score(f"tool-{i}", "2026-01-01T00:00:00", score=1.0))

    compute_fair_distributions("tools", repos)

    variables = {d["variable"] for d in repos.computations.find({})}
    assert {"FAIR_scores_summary", "FAIR_scores_means"} <= variables

    means = repos.computations.find({"variable": "FAIR_scores_means"})[0]
    assert means["data"]["F"] == 1.0
    assert means["collection"] == "tools"
