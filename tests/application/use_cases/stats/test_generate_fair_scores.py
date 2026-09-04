"""
The FAIR stage's tool selection query. The incremental filter is what stops the
stage from fetching and re-checking every one of ~50k tools on every run: a
tool's `last_updated_at` is bumped by merge only when its content changed, so
scoping by it skips unchanged tools without a round-trip.
"""

from application.use_cases.stats.generate_fair_scores import build_tools_query


def test_all_tools_no_filter():
    assert build_tools_query("tools") == {}


def test_tag_filter():
    assert build_tools_query("ELIXIR-ES") == {"data.tags": "ELIXIR-ES"}


def test_updated_since_scopes_all_tools_by_update_time():
    query = build_tools_query("tools", updated_since="2026-08-01T00:00:00")

    assert query == {"last_updated_at": {"$gte": "2026-08-01T00:00:00"}}


def test_updated_since_combines_with_a_tag():
    query = build_tools_query("ELIXIR-ES", updated_since="2026-08-01T00:00:00")

    assert query == {
        "data.tags": "ELIXIR-ES",
        "last_updated_at": {"$gte": "2026-08-01T00:00:00"},
    }


def test_empty_updated_since_is_ignored():
    """A falsy cutoff (from a non-positive window) means score every tool."""
    assert build_tools_query("tools", updated_since=None) == {}
    assert build_tools_query("tools", updated_since="") == {}
