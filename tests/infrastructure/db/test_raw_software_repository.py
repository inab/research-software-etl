"""Tests for the incremental (date-windowed) raw-document query used by the
transformation stage."""

from datetime import datetime

from infrastructure.db.mongo.raw_software_repository import RawSoftwareMetadataRepository
from tests.fakes import FakeDatabaseAdapter


def _doc(_id: str, source: str, updated_at: datetime) -> dict:
    return {"_id": _id, "@data_source": source, "@last_updated_at": updated_at, "data": {}}


def _seed_repo() -> RawSoftwareMetadataRepository:
    db = FakeDatabaseAdapter(
        {
            "alambique": [
                _doc("biotools/old", "biotools", datetime(2026, 1, 1)),
                _doc("biotools/recent", "biotools", datetime(2026, 8, 20)),
                _doc("biotools/edge", "biotools", datetime(2026, 8, 2)),
                _doc("github/recent", "github", datetime(2026, 8, 25)),
            ]
        }
    )
    return RawSoftwareMetadataRepository(db, "alambique")


def _ids(pages) -> set:
    return {doc["_id"] for page in pages for doc in page}


def test_updated_since_none_returns_all_docs_for_source():
    repo = _seed_repo()

    ids = _ids(repo.get_raw_documents_from_source("biotools"))

    assert ids == {"biotools/old", "biotools/recent", "biotools/edge"}


def test_updated_since_filters_out_older_docs():
    repo = _seed_repo()
    cutoff = datetime(2026, 8, 1)

    ids = _ids(repo.get_raw_documents_from_source("biotools", updated_since=cutoff))

    # The Jan doc is dropped; the two on/after the cutoff remain.
    assert ids == {"biotools/recent", "biotools/edge"}


def test_updated_since_is_inclusive_of_the_cutoff():
    repo = _seed_repo()
    cutoff = datetime(2026, 8, 2)

    ids = _ids(repo.get_raw_documents_from_source("biotools", updated_since=cutoff))

    assert "biotools/edge" in ids  # $gte includes an exact match


def test_query_never_crosses_source_boundaries():
    repo = _seed_repo()
    cutoff = datetime(2026, 1, 1)

    ids = _ids(repo.get_raw_documents_from_source("biotools", updated_since=cutoff))

    assert "github/recent" not in ids
