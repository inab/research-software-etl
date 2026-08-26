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

from infrastructure.db.mongo.computations_repository import ComputationsRepository
from infrastructure.db.mongo.embeddings_repository import EmbeddingsRepository
from infrastructure.db.mongo.license_mapping_repository import LicenseMappingRepository
from infrastructure.db.mongo.publications_repository import MongoPublicationRepository
from infrastructure.db.mongo.raw_software_repository import (
    RawSoftwareMetadataRepository,
)
from infrastructure.db.mongo.similarities_repository import SimilaritiesRepository
from infrastructure.db.mongo.standardized_software_repository import PretoolsRepository
from infrastructure.db.mongo.tools_repository import ToolsRepository
from infrastructure.db.mongo.web_availability_repository import (
    WebAvailabilityRepository,
)
from domain.repositories import Repositories
from infrastructure.external.clients import ExternalClients
from infrastructure.external.url_checker import UrlProbe


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


def _project(document: Dict[str, Any], projection: Optional[Dict[str, Any]]) -> dict:
    """
    Inclusion projection, over dotted paths as well as top-level fields.

    The dotted case is not a nicety: the web-availability stage projects
    `{"data.type": 1, "data.webpage": 1}`, and a fake that only understood top-level
    keys would drop `data` altogether -- leaving the stage with no URLs to check and
    a test that passes while proving nothing.

    `_id` comes back unless it is explicitly excluded, as in MongoDB -- code that
    projects `{"source": 1}` still expects to get an id.
    """
    if not projection:
        return document

    included = {k for k, v in projection.items() if v}
    # Suppressing _id alongside inclusions is the one mix MongoDB allows; any other
    # mix is an error there, and we do not need it here.
    excluded = {k for k, v in projection.items() if not v}
    if excluded - {"_id"} and included:
        raise NotImplementedError(
            "FakeDatabaseAdapter: mixed inclusion/exclusion projection"
        )

    if not included:
        return {k: v for k, v in document.items() if k not in excluded}

    if projection.get("_id", 1):
        included.add("_id")

    projected: Dict[str, Any] = {}
    for path in included:
        value = _resolve_path(document, path)
        if value is not _MISSING:
            _set_path(projected, path, value)
    return projected


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


def _set_path(document: Dict[str, Any], path: str, value: Any) -> None:
    """Write a dotted path, as `$set` does -- not a key with a literal dot in it."""
    target = document
    parts = path.split(".")
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = value


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
        self.indexes: Dict[str, List[tuple]] = {}
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

    def find(
        self,
        collection_name: str,
        query: Any,
        projection: Optional[Dict[str, Any]] = None,
        limit: int = 0,
        batch_size: int = 100,
        no_cursor_timeout: bool = True,
    ) -> Iterator[dict]:
        matches = self.fetch_entries(collection_name, query)
        if limit and limit > 0:
            matches = matches[:limit]
        for document in matches:
            yield _project(document, projection)

    def collection_exists(self, collection_name: str) -> bool:
        return collection_name in self.collections

    def list_collection_names(self) -> List[str]:
        return list(self.collections)

    def drop_collection(self, collection_name: str) -> None:
        self.collections.pop(collection_name, None)

    def rename_collection(
        self, collection_name: str, new_name: str, drop_target: bool = False
    ) -> None:
        if collection_name not in self.collections:
            raise KeyError(f"no such collection: {collection_name}")
        if new_name in self.collections and not drop_target:
            raise ValueError(f"target collection already exists: {new_name}")
        self.collections[new_name] = self.collections.pop(collection_name)

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

    def insert_many(
        self, collection_name: str, documents: List[Dict[str, Any]]
    ) -> List[Any]:
        return [self.insert_one(collection_name, document) for document in documents]

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

    def update_custom_upsert(
        self, collection_name: str, criteria: Dict[str, Any], data: Dict[str, Any]
    ) -> None:
        existing = self.fetch_entry(collection_name, criteria)
        if existing is None:
            document = {**copy.deepcopy(criteria), **copy.deepcopy(data)}
            self.insert_one(collection_name, document)
            return
        self.update_entry(collection_name, existing["_id"], data)

    def distinct(
        self, collection_name: str, key: str, query: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        values = []
        for document in self.fetch_entries(collection_name, query or {}):
            value = _resolve_path(document, key)
            if value is not _MISSING and value not in values:
                values.append(value)
        return values

    def create_index(self, collection_name: str, key: str, unique: bool = False) -> str:
        self.indexes.setdefault(collection_name, []).append((key, unique))
        return f"{key}_1"

    def bulk_write(
        self, collection_name: str, operations: List[Any], ordered: bool = False
    ) -> Any:
        """
        Apply pymongo UpdateOne operations.

        The web-availability stage leans on `$push` with `$each`/`$slice` (a rolling
        window of readings) and on `$setOnInsert` (create-if-absent). A fake that
        ignored those would let a broken write look like a passing test, so they are
        interpreted here rather than stubbed.
        """
        applied = 0
        for operation in operations:
            criteria = operation._filter
            update = operation._doc
            upsert = operation._upsert

            document = self.fetch_entry(collection_name, criteria)
            if document is None:
                if not upsert:
                    continue
                document = copy.deepcopy(criteria)
                for key, value in (update.get("$setOnInsert") or {}).items():
                    _set_path(document, key, copy.deepcopy(value))
                self.insert_one(collection_name, document)
                document = self._collection(collection_name)[document["_id"]]

            stored = self._collection(collection_name)[document["_id"]]
            for key, value in (update.get("$set") or {}).items():
                _set_path(stored, key, copy.deepcopy(value))
            for key, spec in (update.get("$push") or {}).items():
                target = _resolve_path(stored, key)
                items = list(target) if isinstance(target, list) else []
                if isinstance(spec, dict) and "$each" in spec:
                    items.extend(copy.deepcopy(spec["$each"]))
                    window = spec.get("$slice")
                    if window is not None and window < 0:
                        items = items[window:]
                else:
                    items.append(copy.deepcopy(spec))
                _set_path(stored, key, items)
            applied += 1

        return applied

    def entry_exists(self, collection_name: str, identifier: Any) -> bool:
        return identifier in self._collection(collection_name)

    def get_entry_metadata(
        self, collection_name: str, identifier: Any
    ) -> Optional[dict]:
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
    tools_staging: bool = False,
    publications: bool = False,
    license_mapping: bool = False,
    computations: bool = False,
    similarities: bool = False,
    embeddings: bool = False,
    web_availability: bool = False,
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
        tools_staging=ToolsRepository(db, "tools_next") if tools_staging else None,
        publications=(
            MongoPublicationRepository(db, "publications") if publications else None
        ),
        license_mapping=(
            LicenseMappingRepository(db, "licenses") if license_mapping else None
        ),
        computations=(
            ComputationsRepository(db, "computations") if computations else None
        ),
        similarities=(
            SimilaritiesRepository(db, "similarities") if similarities else None
        ),
        embeddings=(EmbeddingsRepository(db, "embeddings") if embeddings else None),
        web_availability=(
            WebAvailabilityRepository(db, "webavailability")
            if web_availability
            else None
        ),
    )


class FakeGitHubClient:
    """Records issues and commits instead of touching GitHub."""

    def __init__(self, repo_metadata=None, readme=None) -> None:
        self.issues: List[str] = []
        self.commits: List[str] = []
        self.repo_metadata = repo_metadata or {}
        self.readme = readme

    def commit_file(self, content, path, branch=None, repo=None):
        self.commits.append(path)
        return f"https://github.com/inab/research-software-etl/blob/main/{path}"

    def create_issue(self, title, body, labels=None, repo=None):
        self.issues.append(title)
        return {"html_url": "https://github.com/inab/research-software-etl/issues/1"}

    # Link enrichment reaches for these when a conflict cites a GitHub repository.
    def get_repo_metadata(self, owner, repo_name):
        return self.repo_metadata

    def get_repo_readme(self, owner, repo_name):
        return self.readme


class FakeUrlChecker:
    """
    Every URL answers 200 and redirects to itself.

    `redirects` overrides individual targets, so a test can say "this repo moved"
    without a network: `FakeUrlChecker(redirects={"https://a.org": "https://b.org"})`.
    A URL mapped to None is unreachable.
    """

    def __init__(self, status=200, access_time=0.1, redirects=None) -> None:
        self.status = status
        self.access_time = access_time
        self.redirects = redirects or {}
        self.probed: List[str] = []

    def probe(self, url, timeout=None) -> UrlProbe:
        self.probed.append(url)
        return UrlProbe(self.status, self.access_time)

    def probe_many(self, urls, timeout=None, max_workers=None):
        """Offline stand-in for the concurrent probe: maps ``probe`` over the URLs."""
        for url in urls:
            yield url, self.probe(url, timeout=timeout)

    def resolve_redirects(self, url, timeout=None):
        return self.redirects.get(url, url)


class FakeWebFetcher:
    """
    Stands in for the two things that fetch a page's HTML: the SourceForge client
    (sync) and the headless browser (async). Serves canned HTML, or nothing.
    """

    def __init__(self, html=None) -> None:
        self.html = html
        self.fetched: List[str] = []

    def fetch_html(self, url):  # SourceForgeClient
        self.fetched.append(url)
        return self.html

    async def fetch(self, url):  # HeadlessBrowserFetcher
        self.fetched.append(url)
        return self.html


class FakePyPIClient:
    def __init__(self, info=None) -> None:
        self.info = info

    def get_project_info(self, package_name):
        return self.info


class FakeBitbucketClient:
    def __init__(self, metadata=None, readme=None) -> None:
        self.metadata = metadata or {}
        self.readme = readme

    def get_repo_metadata(self, user, repo):
        return self.metadata

    def get_readme(self, user, repo, metadata):
        return self.readme


def fake_clients(
    *,
    github=None,
    gitlab=None,
    openrouter=None,
    huggingface=None,
    url_checker=None,
    pypi=None,
    sourceforge=None,
    bitbucket=None,
    browser=None,
) -> ExternalClients:
    """
    External clients with only the slots a test exercises filled in.

    The tokened four default to None, so a test that did not ask for GitHub and
    reaches for it raises instead of quietly opening a connection. The tokenless
    fetchers default to offline fakes instead: link enrichment probes every URL a
    conflict happens to carry, and the point of these is that no test can reach
    the network by forgetting one.
    """
    return ExternalClients(
        openrouter=openrouter,
        huggingface=huggingface,
        github=github,
        gitlab=gitlab,
        url_checker=url_checker or FakeUrlChecker(),
        pypi=pypi or FakePyPIClient(),
        sourceforge=sourceforge or FakeWebFetcher(),
        bitbucket=bitbucket or FakeBitbucketClient(),
        browser=browser or FakeWebFetcher(),
    )
