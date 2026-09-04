"""Unit tests for the batched transformation write path: the pure pretools
document builder, the page-level publication resolver, and `process_page`
orchestration (existence + bulk upsert in O(1) round-trips per page)."""

from types import SimpleNamespace

from bson import ObjectId

from infrastructure.config import PipelineConfig
from application.use_cases.transformation import publications_processing, main
from application.use_cases.transformation.software_metadata_processing import (
    build_pretools_document,
    pretools_identifier,
)
from application.use_cases.transformation.publications_processing import (
    resolve_publications_for_page,
)
from tests.fakes import FakeDatabaseAdapter, fake_repos


CONFIG = PipelineConfig()


# --------------------------------------------------------------------------- #
# build_pretools_document (pure)
# --------------------------------------------------------------------------- #

def _software(name="tool", version="1"):
    return {"source": ["biotools"], "name": name, "type": "cmd", "version": [version]}


def test_build_document_for_new_entry_creates_metadata_without_id():
    raw = {"_id": "biotools/tool/cmd/1", "@source_url": None}
    doc = build_pretools_document("biotools/tool/cmd/1", _software(), raw, None, CONFIG)

    # No id/_id in the body -- bulk_upsert supplies _id via the filter.
    assert "_id" not in doc and "id" not in doc
    assert doc["created_at"] == doc["last_updated_at"]
    assert doc["source"][0]["collection"] == CONFIG.alambique_collection
    assert doc["source"][0]["id"] == "biotools/tool/cmd/1"
    assert doc["data"] == _software()


def test_build_document_for_existing_entry_preserves_created_and_bumps_updated():
    existing = {
        "_id": "biotools/tool/cmd/1",
        "created_at": "2020-01-01T00:00:00",
        "created_by": "someone",
        "created_logs": "log",
        "last_updated_at": "2020-01-01T00:00:00",
        "updated_by": "someone",
        "updated_logs": "log",
        "source": [{"collection": "alambiqueDev", "id": "biotools/tool/cmd/1", "source_url": None}],
        "data": {"name": "stale"},
    }
    raw = {"_id": "biotools/tool/cmd/1"}

    doc = build_pretools_document("biotools/tool/cmd/1", _software(name="fresh"), raw, existing, CONFIG)

    assert "_id" not in doc and "id" not in doc
    assert doc["created_at"] == "2020-01-01T00:00:00"      # preserved
    assert doc["last_updated_at"] != "2020-01-01T00:00:00"  # bumped
    assert doc["data"]["name"] == "fresh"


# --------------------------------------------------------------------------- #
# resolve_publications_for_page (batched)
# --------------------------------------------------------------------------- #

class _IdentityStandardizer:
    """Standardizes a raw publication dict to itself."""

    def standardize(self, raw):
        if raw is None:
            return None
        return SimpleNamespace(model_dump=lambda raw=raw: dict(raw))


def test_resolve_reuses_existing_and_inserts_new_pub_once(monkeypatch):
    existing_oid = ObjectId()
    db = FakeDatabaseAdapter(
        {"publications": [{"_id": existing_oid, "data": {"doi": "10.EXIST"}}]}
    )
    repos = fake_repos(db, publications=True)

    # e0 cites the existing pub and a new one; e1 cites the same new one.
    raw_entries = [
        {"_id": "e0", "_pubs": [{"doi": "10.EXIST"}, {"doi": "10.NEW"}]},
        {"_id": "e1", "_pubs": [{"doi": "10.NEW"}]},
    ]
    monkeypatch.setattr(
        publications_processing, "extract_publications",
        lambda source, entry: entry.get("_pubs", []),
    )
    monkeypatch.setattr(
        publications_processing.StandardizerFactory, "get_standardizer",
        staticmethod(lambda source: _IdentityStandardizer()),
    )

    result = resolve_publications_for_page(raw_entries, "biotools", CONFIG, repos)

    # Exactly one new publication document was inserted for the whole page.
    assert len(db.collections["publications"]) == 2
    new_oids = [
        _id for _id in db.collections["publications"] if _id != existing_oid
    ]
    new_oid = new_oids[0]

    assert set(result[0]) == {existing_oid, new_oid}
    assert set(result[1]) == {new_oid}


def test_resolve_returns_empty_for_source_without_publications(monkeypatch):
    repos = fake_repos(FakeDatabaseAdapter(), publications=True)
    result = resolve_publications_for_page([{"_id": "x"}], "github", CONFIG, repos)
    assert result == [[]]


# --------------------------------------------------------------------------- #
# process_page orchestration
# --------------------------------------------------------------------------- #

def test_process_page_upserts_with_publications_and_updates_existing(monkeypatch):
    existing_id = "biotools/existing/cmd/1"
    db = FakeDatabaseAdapter(
        {
            "pretools": [
                {
                    "_id": existing_id,
                    "created_at": "2020-01-01T00:00:00",
                    "created_by": "someone",
                    "created_logs": "log",
                    "last_updated_at": "2020-01-01T00:00:00",
                    "updated_by": "someone",
                    "updated_logs": "log",
                    "source": [{"collection": "alambiqueDev", "id": existing_id, "source_url": None}],
                    "data": {"name": "existing", "stale": True},
                }
            ]
        }
    )
    repos = fake_repos(db, pretools=True)

    raw_entries = [{"_id": "raw0"}, {"_id": "raw1"}]
    software_by_entry = [
        [_software(name="existing")],  # maps to existing_id
        [_software(name="brand_new")],
    ]
    pub_oid = ObjectId()

    monkeypatch.setattr(
        main, "standardize_entry",
        lambda raw_id, raw, source: software_by_entry.pop(0),
    )
    monkeypatch.setattr(
        main, "resolve_publications_for_page",
        lambda entries, source, config, repos: [[pub_oid], []],
    )

    main.process_page(raw_entries, "biotools", CONFIG, repos)

    existing = repos.pretools.get_by_id(existing_id)
    new_id = pretools_identifier(_software(name="brand_new"))
    created = repos.pretools.get_by_id(new_id)

    # Existing entry: created_at preserved, publications attached.
    assert existing["created_at"] == "2020-01-01T00:00:00"
    assert existing["last_updated_at"] != "2020-01-01T00:00:00"
    assert existing["data"]["publication"] == [pub_oid]
    assert "stale" not in existing["data"]  # data replaced, not merged

    # New entry inserted with its _id from the identifier.
    assert created is not None
    assert created["_id"] == new_id
    assert created["data"]["publication"] == []
