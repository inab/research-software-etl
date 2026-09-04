"""Repository-level tests for the batched transformation write path:
``PretoolsRepository.bulk_upsert`` and the publications batch helpers."""

from bson import ObjectId

from infrastructure.db.mongo.standardized_software_repository import PretoolsRepository
from infrastructure.db.mongo.publications_repository import MongoPublicationRepository
from tests.fakes import FakeDatabaseAdapter


def test_bulk_upsert_inserts_new_and_updates_existing_in_one_call():
    db = FakeDatabaseAdapter(
        {"pretools": [{"_id": "s/a/cmd/1", "data": {"name": "a"}, "last_updated_at": "old"}]}
    )
    repo = PretoolsRepository(db, "pretools")

    repo.bulk_upsert(
        {
            "s/a/cmd/1": {"data": {"name": "a2"}, "last_updated_at": "new"},  # update
            "s/b/cmd/1": {"data": {"name": "b"}, "last_updated_at": "new"},   # insert
        }
    )

    updated = repo.get_by_id("s/a/cmd/1")
    inserted = repo.get_by_id("s/b/cmd/1")
    assert updated["data"]["name"] == "a2"
    assert updated["last_updated_at"] == "new"
    assert inserted is not None
    assert inserted["data"]["name"] == "b"
    # _id comes from the filter, not the document body.
    assert inserted["_id"] == "s/b/cmd/1"


def test_bulk_upsert_empty_is_a_noop():
    db = FakeDatabaseAdapter()
    PretoolsRepository(db, "pretools").bulk_upsert({})
    assert db.collections.get("pretools") in (None, {})


def test_find_existing_by_field_matches_in_and_preserves_objectid():
    oid = ObjectId()
    db = FakeDatabaseAdapter(
        {
            "pubs": [
                {"_id": oid, "data": {"doi": "10.1/x", "title": "T"}},
                {"_id": ObjectId(), "data": {"doi": "10.2/y"}},
            ]
        }
    )
    repo = MongoPublicationRepository(db, "pubs")

    found = repo.find_existing_by_field("doi", ["10.1/x", "missing"])

    assert len(found) == 1
    # The id must stay an ObjectId -- pretools stores it as an ObjectId reference.
    assert found[0]["_id"] == oid
    assert isinstance(found[0]["_id"], ObjectId)


def test_find_existing_by_field_skips_empty_values():
    repo = MongoPublicationRepository(FakeDatabaseAdapter(), "pubs")
    assert repo.find_existing_by_field("doi", [None, ""]) == []


def test_save_many_inserts_all_and_returns_ids():
    db = FakeDatabaseAdapter()
    repo = MongoPublicationRepository(db, "pubs")

    ids = repo.save_many([{"data": {"doi": "10.1/x"}}, {"data": {"doi": "10.2/y"}}])

    assert len(ids) == 2
    assert len(db.collections["pubs"]) == 2


def test_save_many_empty_is_a_noop():
    db = FakeDatabaseAdapter()
    assert MongoPublicationRepository(db, "pubs").save_many([]) == []
