"""
Hand-written stand-ins for the things the pipeline talks to.

Fakes, not mocks: the suite injects these into `Repositories` and
`ExternalClients` rather than patching module globals. Patching is what let
tests silently hit a live MongoDB and real LLM endpoints -- and, because the
package installs as `application.*`, a patch target written as
`src.application...` patches a *different* module object and patches nothing at
all.

Slots a test does not exercise stay `None`, so an unexpected reach-through
raises instead of quietly opening a connection.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, Iterator, List, Optional

from bson import ObjectId

from infrastructure.db.mongo.license_mapping_repository import LicenseMappingRepository
from infrastructure.db.mongo.publications_repository import MongoPublicationRepository
from infrastructure.db.mongo.raw_software_repository import RawSoftwareMetadataRepository
from infrastructure.db.mongo.standardized_software_repository import PretoolsRepository
from infrastructure.db.mongo.tools_repository import ToolsRepository
from infrastructure.db.repositories import Repositories
from infrastructure.external.clients import ExternalClients


def _matches(document: Dict[str, Any], query: Dict[str, Any]) -> bool:
    """
    Enough of the MongoDB query language for the pipeline's actual queries:
    dotted paths, `$or`, `$in`/`$nin`, `$exists`, and equality (which matches a
    scalar against a list field, as MongoDB does).
    """
    for key, condition in query.items():
        if key == "$or":
            if not any(_matches(document, clause) for clause in condition):
                return False
            continue

        value = _resolve_path(document, key)

        if isinstance(condition, dict) and any(k.startswith("$") for k in condition):
            for operator, operand in condition.items():
                if operator == "$exists":
                    if (value is not _MISSING) != operand:
                        return False
                elif operator == "$in":
                    if value is _MISSING or value not in operand:
                        return False
                elif operator == "$nin":
                    if value is not _MISSING and value in operand:
                        return False
                elif operator == "$ne":
                    if value == operand:
                        return False
                else:
                    raise NotImplementedError(f"FakeDatabaseAdapter: {operator}")
            continue

        if value is _MISSING:
            return False
        # MongoDB matches a scalar against a list field element-wise.
        if isinstance(value, list) and not isinstance(condition, list):
            if condition not in value:
                return False
        elif value != condition:
            return False

    return True


class _Missing:
    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<missing>"


_MISSING = _Missing()


def _resolve_path(document: Dict[str, Any], path: str) -> Any:
    current: Any = document
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return _MISSING
        current = current[part]
    return current


class FakeDatabaseAdapter:
    """
    An in-memory DatabaseAdapter: `{collection_name: {_id: document}}`.

    Satisfies infrastructure.db.database_adapter.DatabaseAdapter structurally.
    Documents are deep-copied on the way in and out, so a caller mutating what
    it read cannot corrupt the store -- which is what a real database does, and
    what an adapter handing out live dict references would not.
    """

    def __init__(self, collections: Optional[Dict[str, List[dict]]] = None) -> None:
        self.collections: Dict[str, Dict[Any, dict]] = {}
        for name, documents in (collections or {}).items():
            for document in documents:
                self.insert_one(name, copy.deepcopy(document))

    def _collection(self, collection_name: str) -> Dict[Any, dict]:
        return self.collections.setdefault(collection_name, {})

    @staticmethod
    def _as_query(query: Any) -> Dict[str, Any]:
        """PyMongo treats a non-Mapping filter as a bare `_id`; so do we."""
        return query if isinstance(query, dict) else {"_id": query}

    def fetch_entry(self, collection_name: str, query: Any) -> Optional[dict]:
        query = self._as_query(query)
        for document in self._collection(collection_name).values():
            if _matches(document, query):
                return copy.deepcopy(document)
        return None

    def fetch_entries(self, collection_name: str, query: Any) -> List[dict]:
        query = self._as_query(query)
        return [
            copy.deepcopy(document)
            for document in self._collection(collection_name).values()
            if _matches(document, query)
        ]

    def fetch_paginated_entries(
        self, collection_name: str, query: Any, page_size: int = 100
    ) -> Iterator[List[dict]]:
        matches = self.fetch_entries(collection_name, query)
        for start in range(0, len(matches), page_size):
            yield matches[start : start + page_size]

    def insert_one(self, collection_name: str, document: Dict[str, Any]) -> Any:
        document = copy.deepcopy(document)
        if "id" in document:
            document["_id"] = document.pop("id")
        # MongoDB mints an _id when the document has none -- the merge stage
        # relies on it, inserting documents that carry only `source` and `data`.
        if document.get("_id") is None:
            document["_id"] = ObjectId()
        identifier = document["_id"]
        self._collection(collection_name)[identifier] = document
        return identifier

    def update_entry(
        self, collection_name: str, identifier: Any, data: Dict[str, Any]
    ) -> None:
        document = self._collection(collection_name).get(identifier)
        if document is None:
            return
        for key, value in copy.deepcopy(data).items():
            # `$set` understands dotted paths; a plain assignment would create a
            # key with a literal dot in it and the read back would never see it.
            target = document
            parts = key.split(".")
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            target[parts[-1]] = value

    def entry_exists(self, collection_name: str, identifier: Any) -> bool:
        return identifier in self._collection(collection_name)

    def get_entry_metadata(self, collection_name: str, identifier: Any) -> Optional[dict]:
        document = self._collection(collection_name).get(identifier)
        if document is None:
            return None
        return {k: v for k, v in copy.deepcopy(document).items() if k != "data"}


def fake_repos(
    db: Optional[FakeDatabaseAdapter] = None,
    *,
    alambique: bool = False,
    pretools: bool = False,
    tools: bool = False,
    publications: bool = False,
    license_mapping: bool = False,
) -> Repositories:
    """
    A `Repositories` over an in-memory adapter, wiring only what is asked for.

    Opt in to the collections a test exercises; the rest stay None, so a use
    case reaching for a collection the test never wired raises AttributeError
    instead of appearing to work.
    """
    db = db if db is not None else FakeDatabaseAdapter()
    return Repositories(
        alambique=RawSoftwareMetadataRepository(db, "alambique") if alambique else None,
        pretools=PretoolsRepository(db, "pretools") if pretools else None,
        tools=ToolsRepository(db, "tools") if tools else None,
        publications=(
            MongoPublicationRepository(db, "publications") if publications else None
        ),
        license_mapping=(
            LicenseMappingRepository(db, "licenses") if license_mapping else None
        ),
    )


class FakeGitHubClient:
    """Records issues and commits instead of touching GitHub."""

    def __init__(self) -> None:
        self.issues: List[str] = []
        self.commits: List[str] = []

    def commit_file(self, content, path, branch=None, repo=None):
        self.commits.append(path)
        return f"https://github.com/inab/research-software-etl/blob/main/{path}"

    def create_issue(self, title, body, labels=None, repo=None):
        self.issues.append(title)
        return {"html_url": "https://github.com/inab/research-software-etl/issues/1"}


def fake_clients(
    *, github=None, gitlab=None, openrouter=None, huggingface=None
) -> ExternalClients:
    """External clients with only the slots a test exercises filled in."""
    return ExternalClients(
        openrouter=openrouter,
        huggingface=huggingface,
        github=github,
        gitlab=gitlab,
    )
