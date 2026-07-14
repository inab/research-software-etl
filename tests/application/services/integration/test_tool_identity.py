"""
Lineage matching. Pure data in, pure data out -- no database anywhere.
"""

import random

import pytest

from application.services.integration.tool_identity import (
    NewTool,
    PreviousTool,
    assign_identities,
    previous_tool_from_document,
)


def previous(tool_id, sources, first_seen="2024-01-01"):
    return PreviousTool(tool_id=tool_id, sources=frozenset(sources), first_seen=first_seen)


def new(key, sources):
    return NewTool(key=key, sources=frozenset(sources))


def test_an_unchanged_source_set_keeps_its_id():
    prev = previous("A", ["bioconda/x/cmd/1", "biotools/x/cmd/None"])

    result = assign_identities([new("x/cmd", ["bioconda/x/cmd/1", "biotools/x/cmd/None"])], [prev])

    assert result.inherited["x/cmd"].tool_id == "A"
    assert result.retired == []
    assert result.summary(total_new=1) == {"preserved": 1, "new": 0, "retired": 0, "contested": 0}


def test_a_grown_source_set_keeps_its_id():
    """The common case: a registry ships a new version, so a new pretools id appears."""
    prev = previous("A", ["bioconda/x/cmd/1", "biotools/x/cmd/None"])
    grown = new("x/cmd", ["bioconda/x/cmd/1", "biotools/x/cmd/None", "bioconda/x/cmd/2"])

    result = assign_identities([grown], [prev])

    assert result.inherited["x/cmd"].tool_id == "A"


def test_a_shrunk_source_set_keeps_its_id():
    """A cleanup script deleted a pretools entry. Strict superset would churn the id here."""
    prev = previous("A", ["bioconda/x/cmd/1", "biotools/x/cmd/None"])

    result = assign_identities([new("x/cmd", ["bioconda/x/cmd/1"])], [prev])

    assert result.inherited["x/cmd"].tool_id == "A"


def test_a_tool_with_no_shared_lineage_gets_no_ancestor():
    prev = previous("A", ["bioconda/x/cmd/1"])

    result = assign_identities([new("y/cmd", ["bioconda/y/cmd/1"])], [prev])

    assert "y/cmd" not in result.inherited
    assert [p.tool_id for p in result.retired] == ["A"]
    assert result.summary(total_new=1) == {"preserved": 0, "new": 1, "retired": 1, "contested": 0}


def test_when_two_tools_collapse_the_oldest_id_survives():
    old = previous("OLD", ["a"], first_seen="2024-01-01")
    young = previous("YOUNG", ["b", "c"], first_seen="2026-05-01")

    result = assign_identities([new("x/cmd", ["a", "b", "c"])], [old, young])

    assert result.inherited["x/cmd"].tool_id == "OLD"
    assert [p.tool_id for p in result.retired] == ["YOUNG"]
    # The younger tool shared more lineage, so this is exactly the case the
    # contested counter exists to surface.
    assert result.contested == 1


def test_when_a_tool_splits_the_dominant_successor_keeps_the_id():
    prev = previous("A", ["a", "b", "c", "d"])
    big = new("x/cmd", ["a", "b", "c"])
    small = new("y/cmd", ["d"])

    result = assign_identities([big, small], [prev])

    assert result.inherited["x/cmd"].tool_id == "A", "3 shared entries beats 1"
    assert "y/cmd" not in result.inherited, "the other half is a new tool"
    assert result.retired == []


def test_a_previous_id_is_inherited_at_most_once():
    prev = previous("A", ["a", "b"])

    result = assign_identities([new("x/cmd", ["a"]), new("y/cmd", ["b"])], [prev])

    inheritors = [key for key, p in result.inherited.items() if p.tool_id == "A"]
    assert len(inheritors) == 1


def test_the_assignment_does_not_depend_on_input_order():
    previous_tools = [
        previous("A", ["a", "b"], first_seen="2024-01-01"),
        previous("B", ["c"], first_seen="2025-01-01"),
        previous("C", ["d", "e"], first_seen="2023-01-01"),
    ]
    new_tools = [
        new("x/cmd", ["a", "b", "c"]),
        new("y/cmd", ["d"]),
        new("z/cmd", ["e", "f"]),
        new("w/cmd", ["zz"]),
    ]
    expected = {
        key: p.tool_id
        for key, p in assign_identities(new_tools, previous_tools).inherited.items()
    }

    rng = random.Random(0)
    for _ in range(20):
        shuffled_new = new_tools[:]
        shuffled_previous = previous_tools[:]
        rng.shuffle(shuffled_new)
        rng.shuffle(shuffled_previous)

        result = assign_identities(shuffled_new, shuffled_previous)

        assert {k: p.tool_id for k, p in result.inherited.items()} == expected


def test_first_seen_falls_back_to_timestamp_when_absent():
    """Nothing carries first_seen before this feature ships."""
    doc = {"_id": "A", "source": ["a"], "timestamp": "2025-03-01T00:00:00"}

    assert previous_tool_from_document(doc).first_seen == "2025-03-01T00:00:00"


def test_first_seen_wins_over_timestamp_once_it_exists():
    doc = {
        "_id": "A",
        "source": ["a"],
        "first_seen": "2024-01-01T00:00:00",
        "timestamp": "2026-07-01T00:00:00",
    }

    assert previous_tool_from_document(doc).first_seen == "2024-01-01T00:00:00"


def test_a_document_with_no_lineage_is_not_a_candidate():
    assert previous_tool_from_document({"_id": "A", "source": []}) is None


@pytest.mark.parametrize("total_new", [0, 5])
def test_summary_counts_add_up(total_new):
    result = assign_identities([], [previous("A", ["a"])])

    summary = result.summary(total_new=total_new)
    assert summary["preserved"] + summary["new"] == total_new
    assert summary["retired"] == 1
