"""
The fake adapter is only worth anything if it behaves like the real one, so the
cases where it could plausibly drift from MongoDB are pinned here.
"""

import pytest

from tests.fakes import FakeDatabaseAdapter, fake_repos


@pytest.fixture
def db():
    return FakeDatabaseAdapter(
        {
            "pretools": [
                {"_id": "bioconda/abyss/cmd/2.0", "data": {"name": "abyss", "source": ["bioconda"]}},
                {"_id": "biotools/abyss/cmd/None", "data": {"name": "abyss", "source": ["biotools"]}},
            ]
        }
    )


def test_insert_one_renames_id_like_the_real_adapter(db):
    returned = db.insert_one("tools", {"id": "tool-1", "data": {"name": "x"}})

    assert returned == "tool-1"
    assert db.fetch_entry("tools", {"_id": "tool-1"})["data"]["name"] == "x"


def test_bare_identifier_is_treated_as_an_id_filter(db):
    """PyMongo treats a non-Mapping filter as an _id, and get_pub relies on it."""
    assert db.fetch_entry("pretools", "bioconda/abyss/cmd/2.0")["data"]["name"] == "abyss"


def test_equality_matches_inside_a_list_field(db):
    """`{'data.source': 'bioconda'}` must match a document whose source is a list."""
    found = db.fetch_entries("pretools", {"data.source": "bioconda"})

    assert [entry["_id"] for entry in found] == ["bioconda/abyss/cmd/2.0"]


def test_or_and_exists_queries(db):
    found = db.fetch_entries(
        "pretools",
        {"$or": [{"data.name": "abyss"}, {"data.name": "nope"}]},
    )
    assert len(found) == 2

    assert db.fetch_entries("pretools", {"data.missing": {"$exists": True}}) == []
    assert len(db.fetch_entries("pretools", {"data.missing": {"$exists": False}})) == 2


def test_update_entry_understands_dotted_paths(db):
    db.update_entry("pretools", "bioconda/abyss/cmd/2.0", {"data.license": [{"name": "MIT"}]})

    entry = db.fetch_entry("pretools", {"_id": "bioconda/abyss/cmd/2.0"})
    assert entry["data"]["license"] == [{"name": "MIT"}]
    assert entry["data"]["name"] == "abyss", "the dotted update must not clobber siblings"


def test_get_entry_metadata_drops_the_data_field(db):
    metadata = db.get_entry_metadata("pretools", "bioconda/abyss/cmd/2.0")

    assert "data" not in metadata
    assert metadata["_id"] == "bioconda/abyss/cmd/2.0"


def test_reads_are_copies_so_callers_cannot_corrupt_the_store(db):
    entry = db.fetch_entry("pretools", {"_id": "bioconda/abyss/cmd/2.0"})
    entry["data"]["name"] = "mutated"

    assert db.fetch_entry("pretools", {"_id": "bioconda/abyss/cmd/2.0"})["data"]["name"] == "abyss"


def test_paginated_entries_yields_pages():
    db = FakeDatabaseAdapter({"pretools": [{"_id": str(i)} for i in range(5)]})

    pages = list(db.fetch_paginated_entries("pretools", {}, page_size=2))

    assert [len(page) for page in pages] == [2, 2, 1]


def test_unwired_collections_fail_loudly():
    repos = fake_repos(pretools=True)

    assert repos.pretools is not None
    with pytest.raises(AttributeError):
        repos.tools.insert({"_id": "x"})


def test_pretools_repository_over_the_fake(db):
    repos = fake_repos(db, pretools=True)

    assert repos.pretools.exists("bioconda/abyss/cmd/2.0")
    assert repos.pretools.get_by_id("bioconda/abyss/cmd/2.0")["data"]["name"] == "abyss"

    repos.pretools.upsert("new/entry/cmd/1", {"_id": "new/entry/cmd/1", "data": {"name": "n"}})
    assert repos.pretools.exists("new/entry/cmd/1")

    repos.pretools.upsert("new/entry/cmd/1", {"data": {"name": "renamed"}})
    assert repos.pretools.get_by_id("new/entry/cmd/1")["data"]["name"] == "renamed"
    assert len(repos.pretools.get_all()) == 3, "upsert of an existing id must not insert a second"
