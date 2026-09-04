"""
Lineage matching. Pure data in, pure data out -- no database anywhere.
"""

import random

import pytest

from application.services.integration.tool_identity import (
    NewTool,
    PreviousTool,
    assign_identities,
    content_hash,
    previous_tool_from_document,
)


def previous(tool_id, sources, created_at="2024-01-01"):
    return PreviousTool(tool_id=tool_id, sources=frozenset(sources), created_at=created_at)


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
    old = previous("OLD", ["a"], created_at="2024-01-01")
    young = previous("YOUNG", ["b", "c"], created_at="2026-05-01")

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
        previous("A", ["a", "b"], created_at="2024-01-01"),
        previous("B", ["c"], created_at="2025-01-01"),
        previous("C", ["d", "e"], created_at="2023-01-01"),
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


def test_created_at_falls_back_to_update_time_when_absent():
    """A document with only an update time still sorts deterministically."""
    doc = {"_id": "A", "source": ["a"], "last_updated_at": "2025-03-01T00:00:00"}

    assert previous_tool_from_document(doc).created_at == "2025-03-01T00:00:00"


def test_created_at_wins_over_update_time_once_it_exists():
    doc = {
        "_id": "A",
        "source": ["a"],
        "created_at": "2024-01-01T00:00:00",
        "last_updated_at": "2026-07-01T00:00:00",
    }

    assert previous_tool_from_document(doc).created_at == "2024-01-01T00:00:00"


def test_a_document_with_no_lineage_is_not_a_candidate():
    assert previous_tool_from_document({"_id": "A", "source": []}) is None


def test_previous_tool_reads_new_field_names():
    doc = {
        "_id": "A",
        "source": ["a"],
        "created_at": "2024-01-01T00:00:00",
        "last_updated_at": "2026-07-01T00:00:00",
        "content_hash": "deadbeef",
    }

    previous = previous_tool_from_document(doc)
    assert previous.created_at == "2024-01-01T00:00:00"
    assert previous.last_updated_at == "2026-07-01T00:00:00"
    assert previous.content_hash == "deadbeef"


def test_previous_tool_reads_pre_rename_field_names():
    """A collection written before the rename still hands its dates across."""
    doc = {
        "_id": "A",
        "source": ["a"],
        "first_seen": "2024-01-01T00:00:00",
        "timestamp": "2026-07-01T00:00:00",
    }

    previous = previous_tool_from_document(doc)
    assert previous.created_at == "2024-01-01T00:00:00"
    assert previous.last_updated_at == "2026-07-01T00:00:00"


def test_previous_tool_defaults_update_time_and_hash_when_absent():
    """Tools written before content hashing carry neither field."""
    previous = previous_tool_from_document({"_id": "A", "source": ["a"]})

    assert previous.last_updated_at == ""
    assert previous.content_hash == ""


class TestContentHash:
    def test_identical_content_hashes_equal(self):
        data = {"name": "trimal", "source_code": ["a", "b"]}

        assert content_hash(data) == content_hash(dict(data))

    def test_list_order_does_not_change_the_hash(self):
        """
        The merge validators call list(set(...)), so list order is not stable
        run to run. The fingerprint must ignore it or it would flip constantly.
        """
        a = {"name": "trimal", "source_code": ["a", "b", "c"], "version": ["1", "2"]}
        b = {"name": "trimal", "source_code": ["c", "a", "b"], "version": ["2", "1"]}

        assert content_hash(a) == content_hash(b)

    def test_nested_list_order_does_not_change_the_hash(self):
        a = {"repository": [{"url": "x", "kind": "git"}, {"url": "y"}]}
        b = {"repository": [{"url": "y"}, {"kind": "git", "url": "x"}]}

        assert content_hash(a) == content_hash(b)

    def test_a_real_content_change_changes_the_hash(self):
        a = {"name": "trimal", "source_code": ["a", "b"]}
        b = {"name": "trimal", "source_code": ["a", "b", "c"]}

        assert content_hash(a) != content_hash(b)

    def test_key_order_does_not_change_the_hash(self):
        assert content_hash({"a": 1, "b": 2}) == content_hash({"b": 2, "a": 1})


@pytest.mark.parametrize("total_new", [0, 5])
def test_summary_counts_add_up(total_new):
    result = assign_identities([], [previous("A", ["a"])])

    summary = result.summary(total_new=total_new)
    assert summary["preserved"] + summary["new"] == total_new
    assert summary["retired"] == 1
