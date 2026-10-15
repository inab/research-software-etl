"""
Use case: generate synthetic search queries for tools and store them in the
``semantic_search`` collection, one document per tool.

Two ways to run the LLM, sharing the prompt, the parsing and the incremental rules
of ``services/semantic_search/synthetic_queries.py``:

- ``generate_synthetic_queries`` -- online, one Gepeto call per tool.
- ``export_query_requests`` / ``import_query_results`` -- offline. Export the
  prompts, run them as a batch job on MareNostrum 5 (``hpc/mn5/``), import the raw
  completions. MN5 compute nodes cannot reach MongoDB, hence the hand-off.

Incremental: a tool is (re)generated only when it has no document yet, or when
what the LLM would be shown (``input_hash``) or the prompt (``PROMPT_VERSION``)
has changed since. Tool ids survive merges (see ``tool_identity.py``), so
``tool_id`` is a stable key across runs. Tools too thin to prompt are stored as
``insufficient`` without an LLM call.

Prompt version 2 (``README_PROMPT_VERSION``) adds the tool's GitHub README,
looked up through a ``ReadmeSource`` (a cache in front of the github-metadata-api;
see ``readme_repos`` for which tools get one). Import needs the same source, to
recompute the ``input_hash`` a v2 result was exported with. Failures are not stored, so they are
retried next time. Documents of tools that no longer exist are removed whenever
the run covers the whole collection (no tag).

File I/O stays in the CLI: export returns the requests, import takes the results.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional, Protocol, Tuple

from application.services.semantic_search.synthetic_queries import (
    CONTEXT_PROJECTION,
    PROMPT_VERSION,
    QUERY_SCHEMA,
    README_PROMPT_VERSION,
    README_REPO_PROJECTION,
    STATUS_INSUFFICIENT,
    VOCABULARY_PROJECTION,
    QueryRequest,
    QueryResult,
    build_document,
    build_request,
    is_current,
    readme_repos,
    result_from_completion,
    vocabulary,
)
from domain.repositories import Repositories

logger = logging.getLogger(__name__)


class ChatClient(Protocol):
    """What the online path needs from Gepeto (``GepetoClient`` satisfies it)."""

    def query(
        self, messages: Any, model: str, temperature: float = 0.2
    ) -> tuple[str, dict]: ...


Repo = Tuple[str, str]


class ReadmeSource(Protocol):
    """Raw READMEs by (owner, repo); None for a repository without one."""

    def readmes(self, repos: Iterable[Repo]) -> Dict[Repo, Optional[str]]: ...


@dataclass
class Summary:
    generated: int = 0
    insufficient: int = 0
    failed: int = 0
    unchanged: int = 0
    removed: int = 0
    exported: int = 0
    stale: int = 0
    deferred: int = 0

    def line(self) -> str:
        return " / ".join(f"{k}={v}" for k, v in self.__dict__.items())


@dataclass
class _Plan:
    # Tools that need an LLM call, capped at `limit`.
    pending: List[QueryRequest] = field(default_factory=list)
    # Tools too thin to prompt: stored as insufficient without a call.
    thin: List[QueryRequest] = field(default_factory=list)
    live_ids: set[str] = field(default_factory=set)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _scope_query(tag: Optional[str]) -> dict:
    return {} if tag in (None, "tools") else {"data.tags": tag}


def _no_readme(tool_id: str) -> Optional[str]:
    return None


def _readme_lookup(
    repos: Repositories,
    readmes: Optional[ReadmeSource],
    scope: Optional[set[str]] = None,
) -> Callable[[str], Optional[str]]:
    """tool_id -> raw README, for the tools in ``scope`` (None: every tool)."""
    if readmes is None:
        raise ValueError(f"Prompt version {README_PROMPT_VERSION} needs READMEs")
    # Over every tool whatever the scope: a repository is shared or not
    # collection-wide.
    repo_of = readme_repos(
        repos.tools.iter_projected({}, README_REPO_PROJECTION, batch_size=2000)
    )
    if scope is not None:
        repo_of = {k: v for k, v in repo_of.items() if k in scope}
    texts = readmes.readmes(set(repo_of.values()))
    logger.info(
        f"READMEs: {sum(1 for r in repo_of.values() if texts.get(r))} of "
        f"{len(repo_of)} eligible tools have one"
    )
    return lambda tool_id: texts.get(repo_of[tool_id]) if tool_id in repo_of else None


def _plan(
    repos: Repositories,
    summary: Summary,
    tag: Optional[str],
    limit: Optional[int],
    force: bool,
    prompt_version: str = PROMPT_VERSION,
    readmes: Optional[ReadmeSource] = None,
) -> _Plan:
    stored = repos.semantic_search.fingerprints()
    readme_of: Callable[[str], Optional[str]] = _no_readme
    if prompt_version == README_PROMPT_VERSION:
        scope = (
            None
            if tag in (None, "tools")
            else {
                str(t["_id"])
                for t in repos.tools.iter_projected(_scope_query(tag), {"_id": 1})
            }
        )
        readme_of = _readme_lookup(repos, readmes, scope)
    # Over every tool whatever the scope, so a tool's name filter does not depend
    # on which tag it was generated under.
    vocab = vocabulary(
        tool.get("data")
        for tool in repos.tools.iter_projected(
            {}, VOCABULARY_PROJECTION, batch_size=2000
        )
    )
    plan = _Plan()
    for tool in repos.tools.iter_projected(
        _scope_query(tag), CONTEXT_PROJECTION, batch_size=1000
    ):
        request = build_request(
            tool,
            readme_of(str(tool["_id"])),
            prompt_version=prompt_version,
            vocab=vocab,
        )
        plan.live_ids.add(request.tool_id)
        if not force and is_current(request, stored.get(request.tool_id)):
            summary.unchanged += 1
        elif request.context is None:
            plan.thin.append(request)
        elif limit is None or len(plan.pending) < limit:
            plan.pending.append(request)
        else:
            summary.deferred += 1
    return plan


def _store_thin_and_prune(
    repos: Repositories, plan: _Plan, summary: Summary, tag: Optional[str]
) -> None:
    now = _utc_now_iso()
    for request in plan.thin:
        repos.semantic_search.upsert_by_tool_id(
            build_document(request, QueryResult(STATUS_INSUFFICIENT), None, now)
        )
        summary.insufficient += 1
    # Only a whole-collection scan knows every live tool; a tag scope does not.
    if tag in (None, "tools"):
        summary.removed = repos.semantic_search.delete_except(plan.live_ids)


def _record(
    repos: Repositories,
    request: QueryRequest,
    result: Optional[QueryResult],
    model: Optional[str],
    summary: Summary,
    dry_run: bool,
) -> None:
    if result is None:
        summary.failed += 1
        logger.warning(f"[FAIL] tool_id={request.tool_id} ({request.tool_name})")
        return
    if result.status == STATUS_INSUFFICIENT:
        summary.insufficient += 1
    else:
        summary.generated += 1
    if dry_run:
        print(f"\n{request.tool_name} [{request.tool_id}] -> {result.status}")
        for query in result.queries:
            print(f"  - {query}")
        return
    repos.semantic_search.upsert_by_tool_id(
        build_document(request, result, model, _utc_now_iso())
    )


def generate_synthetic_queries(
    repos: Repositories,
    client: ChatClient,
    model: str,
    *,
    tag: Optional[str] = None,
    limit: Optional[int] = None,
    force: bool = False,
    workers: int = 4,
    temperature: float = 0.5,
    dry_run: bool = False,
    prompt_version: str = PROMPT_VERSION,
    readmes: Optional[ReadmeSource] = None,
) -> Summary:
    """Generate queries online, one LLM call per tool, storing each as it arrives."""
    summary = Summary()
    if not dry_run:
        repos.semantic_search.ensure_tool_id_index()
    plan = _plan(repos, summary, tag, limit, force, prompt_version, readmes)
    if not dry_run:
        _store_thin_and_prune(repos, plan, summary, tag)

    logger.info(f"Generating queries for {len(plan.pending)} tools with {model}")

    def ask(request: QueryRequest) -> Optional[QueryResult]:
        try:
            raw, _ = client.query(
                request.messages(), model=model, temperature=temperature
            )
        except Exception as exc:
            logger.warning(f"LLM call failed for {request.tool_id}: {exc}")
            return None
        return result_from_completion(request, raw)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(ask, request): request for request in plan.pending}
        for done, future in enumerate(as_completed(futures), start=1):
            _record(repos, futures[future], future.result(), model, summary, dry_run)
            if done % 100 == 0:
                logger.info(f"{done}/{len(futures)} -- {summary.line()}")
    return summary


def export_query_requests(
    repos: Repositories,
    *,
    tag: Optional[str] = None,
    limit: Optional[int] = None,
    force: bool = False,
    prompt_version: str = PROMPT_VERSION,
    readmes: Optional[ReadmeSource] = None,
) -> tuple[List[dict], Summary]:
    """
    The prompts of every tool that needs queries, as JSON-serializable dicts.

    Each carries its own ``messages`` (so the batch job needs no knowledge of the
    prompt) and the fields ``import_query_results`` needs to store the answer.
    Thin tools are stored as insufficient right away; they need no LLM.
    """
    summary = Summary()
    repos.semantic_search.ensure_tool_id_index()
    plan = _plan(repos, summary, tag, limit, force, prompt_version, readmes)
    _store_thin_and_prune(repos, plan, summary, tag)
    requests = [
        {
            "id": request.tool_id,
            "tool_name": request.tool_name,
            "names": request.names,
            "input_hash": request.input_hash,
            "prompt_version": request.prompt_version,
            "messages": request.messages(),
            "json_schema": QUERY_SCHEMA,
        }
        for request in plan.pending
    ]
    summary.exported = len(requests)
    return requests, summary


def import_query_results(
    repos: Repositories,
    results: Iterable[dict],
    readmes: Optional[ReadmeSource] = None,
) -> Summary:
    """
    Store the batch job's completions.

    A result whose ``input_hash`` no longer matches its tool (the tool changed, or
    was retired, after the export) is skipped as stale: storing it would overwrite
    queries generated from newer input. The next export picks that tool up again.

    Version-2 results need ``readmes`` -- the same README source as the export, so
    the hash comes out the same; without it they are all stale.
    """
    summary = Summary()
    repos.semantic_search.ensure_tool_id_index()
    readme_of: Callable[[str], Optional[str]] = _no_readme
    if readmes is not None:
        readme_of = _readme_lookup(repos, readmes)
    # (tool_id, prompt_version) -> input_hash, for both versions.
    current = {}
    for tool in repos.tools.iter_projected({}, CONTEXT_PROJECTION, batch_size=1000):
        tool_id = str(tool["_id"])
        current[(tool_id, PROMPT_VERSION)] = build_request(tool).input_hash
        if readmes is not None:
            current[(tool_id, README_PROMPT_VERSION)] = build_request(
                tool, readme_of(tool_id), prompt_version=README_PROMPT_VERSION
            ).input_hash
    for item in results:
        request = QueryRequest(
            tool_id=item["id"],
            tool_name=item.get("tool_name", ""),
            names=item.get("names") or [],
            input_hash=item["input_hash"],
            context=None,
            prompt_version=item["prompt_version"],
        )
        if current.get((request.tool_id, request.prompt_version)) != request.input_hash:
            summary.stale += 1
            continue
        if item.get("error"):
            summary.failed += 1
            continue
        result = result_from_completion(request, item.get("completion") or "")
        _record(repos, request, result, item.get("model"), summary, dry_run=False)
    return summary
