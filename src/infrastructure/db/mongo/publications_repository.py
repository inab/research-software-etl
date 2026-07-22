from __future__ import annotations

from typing import Any, Iterable, Optional

from bson import ObjectId
from bson.errors import InvalidId

from infrastructure.db.database_adapter import DatabaseAdapter


def _to_oid(identifier: Any) -> Any:
    """Coerce a str id into an ``ObjectId`` for querying the ObjectId-keyed
    publications collection. A str that isn't a valid ObjectId is left as-is (it will
    simply match nothing here); already-``ObjectId`` (or anything else) passes through."""
    if isinstance(identifier, str):
        try:
            return ObjectId(identifier)
        except InvalidId:
            return identifier
    return identifier


def _stringify_id(doc: Optional[dict]) -> Optional[dict]:
    """Coerce a document's ``_id`` from ``ObjectId`` to ``str`` so the application
    layer never sees a bson type. Returns the doc unchanged if it has no ObjectId id."""
    if doc and isinstance(doc.get("_id"), ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc


class MongoPublicationRepository:
    def __init__(
        self,
        db_adapter: DatabaseAdapter,
        collection_name: str = "publicationsMetadataDev",
    ) -> None:
        self.mongo_db = db_adapter
        self.collection_name = collection_name

    def get_by_id(self, identifier: Any):
        """Find a publication metadata entry by its identifier."""
        return _stringify_id(
            self.mongo_db.fetch_entry(self.collection_name, _to_oid(identifier))
        )

    def get_all(self) -> list[dict]:
        return [
            _stringify_id(doc)
            for doc in self.mongo_db.fetch_entries(self.collection_name, {})
        ]

    def find_by_doi(self, doi: str):
        """Find a publication metadata entry by DOI."""
        query = {"data.doi": doi}
        return _stringify_id(self.mongo_db.fetch_entry(self.collection_name, query))

    def find_by_title(self, title: str):
        """Find a publication metadata entry by title."""
        query = {"data.title": title}
        return _stringify_id(self.mongo_db.fetch_entry(self.collection_name, query))

    def find_by_url(self, url: str):
        """Find a publication metadata entry by URL."""
        query = {"data.url": url}
        return _stringify_id(self.mongo_db.fetch_entry(self.collection_name, query))

    def find_by_pmid(self, pmid: str):
        """Find a publication metadata entry by PMID."""
        query = {"data.pmid": pmid}
        return _stringify_id(self.mongo_db.fetch_entry(self.collection_name, query))

    def find_by_pmcid(self, pmcid: str):
        """Find a publication metadata entry by PMCID."""
        query = {"data.pmcid": pmcid}
        return _stringify_id(self.mongo_db.fetch_entry(self.collection_name, query))

    def entry_exists(self, identifier: str) -> bool:
        return self.mongo_db.entry_exists(self.collection_name, _to_oid(identifier))

    def get_metadata(self, identifier: str):
        return _stringify_id(
            self.mongo_db.get_entry_metadata(self.collection_name, _to_oid(identifier))
        )

    def save_entry(self, document: dict):
        return self.mongo_db.insert_one(self.collection_name, document)

    def fetch_with_doi(self, collection_name: str) -> Iterable[dict[str, Any]]:
        query = {
            "data.doi": {
                "$exists": True,
                "$nin": [None, ""],
            }
        }
        return self.mongo_db.fetch_entries(collection_name, query)

    def fetch_without_doi(self, collection_name: str) -> Iterable[dict[str, Any]]:
        query = {
            "$or": [
                {"data.doi": {"$exists": False}},
                {"data.doi": None},
                {"data.doi": ""},
            ]
        }
        return self.mongo_db.fetch_entries(collection_name, query)

    def update_publication_data(
        self,
        collection_name: str,
        document_id: Any,
        data: dict[str, Any],
        last_updated_at: str,
    ) -> None:
        self.mongo_db.update_entry(
            collection_name,
            _to_oid(document_id),
            {
                "data": data,
                "last_updated_at": last_updated_at,
            },
        )

    def update_publication_doi(
        self,
        collection_name: str,
        document_id: Any,
        doi: str,
        doi_resolution_source: str | None = None,
        doi_resolution_confidence: float | None = None,
        doi_resolution_match_title: str | None = None,
        doi_resolution_match_journal: str | None = None,
        doi_resolution_match_year: int | None = None,
        last_updated_at: str | None = None,
    ) -> None:
        update_data: dict[str, Any] = {
            "data.doi": doi,
        }

        if doi_resolution_source is not None:
            update_data["meta.doi_resolution_source"] = doi_resolution_source

        if doi_resolution_confidence is not None:
            update_data["meta.doi_resolution_confidence"] = doi_resolution_confidence

        if doi_resolution_match_title is not None:
            update_data["meta.doi_resolution_match_title"] = doi_resolution_match_title

        if doi_resolution_match_journal is not None:
            update_data["meta.doi_resolution_match_journal"] = doi_resolution_match_journal

        if doi_resolution_match_year is not None:
            update_data["meta.doi_resolution_match_year"] = doi_resolution_match_year

        if last_updated_at is not None:
            update_data["last_updated_at"] = last_updated_at

        self.mongo_db.update_entry(
            collection_name,
            _to_oid(document_id),
            update_data,
        )