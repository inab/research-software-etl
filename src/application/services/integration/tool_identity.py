"""
Carry tool identities across runs.

The merge stage rebuilds every tool from scratch, so without this a tool's ``_id``
lives exactly one run -- and everything keyed on it (FAIR scores in
``computationsDev.createdFrom``, neighbours in ``similaritiesDev.tool_id``, any
external bookmark) points at a document that no longer exists.

A tool's lineage is the set of pretools entries it was merged from -- its
``source`` list. This module matches each newly merged tool against the previous
run's tools on that lineage and hands down the ``_id`` of the one it most
plausibly continues.

Nothing here touches a database: it is a pure function of two lists, so every
branch below is exercised offline.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Hashable, Iterable, Optional


def _canonicalize(value: Any) -> Any:
    """
    Rewrite ``value`` into a form whose JSON serialization does not depend on
    list order.

    The merged tool ``data`` is built through pydantic validators that call
    ``list(set(...))`` (``source_code``, ``description``, ...), so the order of
    those lists is not stable from one run to the next even when the content is
    identical. Sorting every list here makes the fingerprint order-insensitive:
    it flips only when the *set* of values changes, not when they are shuffled.

    The trade-off is that a change consisting solely of reordering a list (e.g.
    which ``version`` is listed first) is not seen as a change. FAIR indicators
    key on presence and counts rather than position, so this is acceptable.
    """
    if isinstance(value, dict):
        return {key: _canonicalize(val) for key, val in value.items()}
    if isinstance(value, list):
        canon = [_canonicalize(item) for item in value]
        return sorted(canon, key=lambda item: json.dumps(item, sort_keys=True, default=str))
    return value


def content_hash(data: dict) -> str:
    """
    A stable fingerprint of a tool's ``data`` payload.

    Two merged tools with the same content produce the same hash regardless of
    run-to-run list ordering, so merge can tell whether a tool actually changed
    since the previous run. Pure: no clock, no database, no iteration-order
    dependence.
    """
    payload = json.dumps(_canonicalize(data), sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PreviousTool:
    """A tool as the last run left it: its id, its lineage, and when it appeared."""

    tool_id: Any
    sources: frozenset[str]
    # When the tool first appeared (mirrors pretools' `created_at`).
    created_at: str
    # The last merge that changed the tool's content and its content fingerprint
    # (mirrors pretools' `last_updated_at`). Both default to empty so a first run
    # -- whose tools predate this feature -- reads as "no known content", which
    # forces a fresh timestamp and a recompute downstream.
    last_updated_at: str = ""
    content_hash: str = ""


@dataclass(frozen=True)
class NewTool:
    """A tool this run just merged, not yet given an identity."""

    key: str  # the disambiguation block key, e.g. "mapcaller/cmd" -- stable tie-break
    sources: frozenset[str]


@dataclass
class IdentityAssignment:
    """Which previous id each new tool inherits, and what became of the rest."""

    inherited: dict[str, PreviousTool] = field(default_factory=dict)
    retired: list[PreviousTool] = field(default_factory=list)
    contested: int = 0

    @property
    def preserved_count(self) -> int:
        return len(self.inherited)

    def summary(self, total_new: int) -> dict[str, int]:
        return {
            "preserved": self.preserved_count,
            "new": total_new - self.preserved_count,
            "retired": len(self.retired),
            "contested": self.contested,
        }


def _sort_key(edge: tuple[NewTool, PreviousTool, int]) -> tuple:
    new, previous, overlap = edge
    # Oldest previous tools claim first, so when several of them collapse into one
    # new tool the oldest id is the one that survives. Within a single previous
    # tool, it goes to the successor it overlaps most -- so when a tool splits, the
    # dominant half keeps the id and the other half is treated as new.
    #
    # `str(previous.tool_id)` and the block key make the order total: the result
    # must not depend on dict or cursor iteration order.
    return (previous.created_at, str(previous.tool_id), -overlap, new.key)


def assign_identities(
    new_tools: Iterable[NewTool], previous_tools: Iterable[PreviousTool]
) -> IdentityAssignment:
    """
    Match new tools to previous ones by lineage overlap.

    A new tool inherits from the previous tool it shares the most pretools entries
    with; each previous id can be inherited at most once. New tools with no
    surviving ancestor get no entry here -- the caller mints a fresh id. Previous
    tools nobody claimed are retired (the archived collection still holds them).
    """
    new_tools = list(new_tools)
    previous_tools = list(previous_tools)

    # An inverted index over lineage, so we compare each new tool only against the
    # previous tools that actually share an entry with it. Comparing every pair
    # would be ~50k x ~50k.
    by_source: dict[str, list[PreviousTool]] = {}
    for previous in previous_tools:
        for source_id in previous.sources:
            by_source.setdefault(source_id, []).append(previous)

    edges: list[tuple[NewTool, PreviousTool, int]] = []
    for new in new_tools:
        overlaps: dict[Hashable, int] = {}
        candidates: dict[Hashable, PreviousTool] = {}
        for source_id in new.sources:
            for previous in by_source.get(source_id, ()):
                overlaps[previous.tool_id] = overlaps.get(previous.tool_id, 0) + 1
                candidates[previous.tool_id] = previous
        for tool_id, overlap in overlaps.items():
            edges.append((new, candidates[tool_id], overlap))

    edges.sort(key=_sort_key)

    assignment = IdentityAssignment()
    claimed_previous: set[Hashable] = set()
    best_overlap = _best_overlap_per_new_tool(edges)

    for new, previous, overlap in edges:
        if new.key in assignment.inherited or previous.tool_id in claimed_previous:
            continue
        assignment.inherited[new.key] = previous
        claimed_previous.add(previous.tool_id)
        # "Oldest wins" can hand a tool to an ancient ancestor sharing one entry
        # over a younger one sharing twenty. Count that, so a real run can say how
        # often it happens rather than leaving it to be argued about.
        if overlap < best_overlap[new.key]:
            assignment.contested += 1

    assignment.retired = [
        previous
        for previous in previous_tools
        if previous.tool_id not in claimed_previous
    ]

    return assignment


def _best_overlap_per_new_tool(
    edges: list[tuple[NewTool, PreviousTool, int]]
) -> dict[str, int]:
    best: dict[str, int] = {}
    for new, _previous, overlap in edges:
        if overlap > best.get(new.key, 0):
            best[new.key] = overlap
    return best


def previous_tool_from_document(document: dict) -> Optional[PreviousTool]:
    """
    Read a tool document from the live collection as a lineage record.

    The timestamp fields were renamed to mirror pretools (``first_seen`` ->
    ``created_at``, ``timestamp`` -> ``last_updated_at``), so both names are read
    here: a live collection written before the rename still carries the old ones,
    and this is what lets identities carry across that first post-rename run.
    ``created_at`` further falls back to the update time, so a document with no
    creation date at all still sorts deterministically (oldest-wins simply has
    nothing to bite on until real creation dates exist).
    """
    sources = document.get("source") or []
    if not sources:
        return None
    created_at = (
        document.get("created_at")
        or document.get("first_seen")
        or document.get("last_updated_at")
        or document.get("timestamp")
        or ""
    )
    last_updated_at = document.get("last_updated_at") or document.get("timestamp") or ""
    return PreviousTool(
        tool_id=document["_id"],
        sources=frozenset(sources),
        created_at=created_at,
        last_updated_at=last_updated_at,
        content_hash=document.get("content_hash") or "",
    )
