"""
Synthetic search queries for a tool: the prompt that asks an LLM for them, and
the parsing that turns its answer into a stored document.

Semantic search matches a user's query against queries written *for* each tool
(dense retrieval over synthetic queries), so what matters here is that the queries
are the kind a researcher would type, and specific enough to single the tool out.

Everything in this module is pure. The LLM call itself happens elsewhere: online
through Gepeto (`use_cases/semantic_search`), or offline as a batch job on
MareNostrum 5 (`hpc/mn5/`). Both paths use this prompt and this parser, so a
record gets the same treatment whichever way its queries were generated.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional

# Bump when SYSTEM_PROMPT or build_tool_context change in a way that should
# regenerate every tool's queries.
PROMPT_VERSION = "1"

MAX_QUERIES = 6
MIN_WORDS = 3
MAX_WORDS = 15
MAX_DESCRIPTION_CHARS = 2000

STATUS_GENERATED = "generated"
# Stored, so a thin record is not re-asked every run. It is regenerated as soon
# as its input changes.
STATUS_INSUFFICIENT = "insufficient"

# The tool fields build_tool_context reads -- the projection callers stream.
CONTEXT_PROJECTION = {
    "_id": 1,
    "data.name": 1,
    "data.label": 1,
    "data.type": 1,
    "data.description": 1,
    "data.documentation": 1,
    "data.topics": 1,
    "data.operations": 1,
    "data.input": 1,
    "data.output": 1,
}

SYSTEM_PROMPT = f"""You write search queries that researchers would type into a \
life-science research software registry to find a specific tool.

Given a tool record, write up to {MAX_QUERIES} diverse queries ({MIN_WORDS}-{MAX_WORDS} \
words each) for which this tool is a strong, specific answer.

Rules:
- Phrase each query as a researcher's need: the task, the data types, the file \
formats, the organisms, the method or the domain, stated concretely.
- Vary the angle across queries (task, input data, output, domain, method); do not \
paraphrase the same query.
- Never include the tool's name or label.
- No generic queries such as "bioinformatics tool", "data analysis software" or \
"process files".
- Use only information present in the record; do not invent capabilities.
- If the record lacks enough specific information to write useful queries, return \
an empty list.

Respond with JSON only, no commentary: {{"queries": ["...", "..."]}}"""


# The answer's shape. Exported with each request so the MN5 job can constrain
# decoding to it (vLLM structured outputs); parse_queries still validates.
QUERY_SCHEMA = {
    "type": "object",
    "properties": {
        "queries": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": MAX_QUERIES,
        }
    },
    "required": ["queries"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class QueryRequest:
    """One tool's prompt, plus what is needed to store the answer."""

    tool_id: str
    tool_name: str
    # Name and labels; queries that contain any of them are dropped.
    names: List[str]
    input_hash: str
    # None when the record is too thin to prompt at all.
    context: Optional[str]
    prompt_version: str = PROMPT_VERSION

    def messages(self) -> List[dict]:
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": self.context or ""},
        ]


@dataclass
class QueryResult:
    status: str
    queries: List[str] = field(default_factory=list)


def _terms(items: Any) -> List[str]:
    terms = {
        item["term"].strip()
        for item in items or []
        if isinstance(item, dict) and isinstance(item.get("term"), str)
    }
    return sorted(t for t in terms if t)


def _descriptions(data: dict) -> List[str]:
    """Distinct descriptions, longest first; the `help` documentation as fallback."""
    raw = [d.strip() for d in data.get("description") or [] if isinstance(d, str)]
    seen: set[str] = set()
    distinct = []
    # Longest first, ties broken by text: merge does not keep list order stable
    # between runs, and an order change must not change `input_hash`.
    for text in sorted((d for d in raw if d), key=lambda d: (-len(d), d)):
        if text.lower() not in seen:
            seen.add(text.lower())
            distinct.append(text)
    if distinct:
        return distinct

    for item in data.get("documentation") or []:
        if (
            isinstance(item, dict)
            and item.get("type") == "help"
            and isinstance(item.get("content"), str)
            and item["content"].strip()
        ):
            return [item["content"].strip()]
    return []


def build_tool_context(data: dict) -> Optional[str]:
    """
    The record as the LLM sees it, or None when there is nothing to go on.

    None means no description, no help text and no EDAM topics or operations --
    a name alone is not enough to write specific queries. Anything more goes to
    the LLM, which makes the final call: short Galaxy descriptions ("In aligned
    Bam files.") read fine next to the name ("bbtools_callvariants").
    """
    descriptions = _descriptions(data)
    topics = _terms(data.get("topics"))
    operations = _terms(data.get("operations"))
    if not descriptions and not topics and not operations:
        return None

    lines = [f"Name: {data.get('name') or ''}"]
    types = [t for t in data.get("type") or [] if isinstance(t, str)]
    if types:
        lines.append(f"Type: {', '.join(sorted(set(types)))}")
    if descriptions:
        lines.append(
            "Description:\n" + "\n".join(descriptions)[:MAX_DESCRIPTION_CHARS].strip()
        )
    for label, terms in (
        ("Topics", topics),
        ("Operations", operations),
        ("Input formats", _terms(data.get("input"))),
        ("Output formats", _terms(data.get("output"))),
    ):
        if terms:
            lines.append(f"{label}: {', '.join(terms)}")
    return "\n".join(lines)


def input_hash(context: Optional[str]) -> str:
    """
    Fingerprint of what the LLM is shown.

    Deliberately not the tool's `content_hash`: that changes whenever a version or
    download URL does, which says nothing about what the tool is for.
    """
    return hashlib.sha256((context or "").encode("utf-8")).hexdigest()


def build_request(tool: dict) -> QueryRequest:
    data = tool.get("data") or {}
    name = data.get("name") or ""
    labels = [label for label in data.get("label") or [] if isinstance(label, str)]
    context = build_tool_context(data)
    return QueryRequest(
        tool_id=str(tool["_id"]),
        tool_name=name,
        names=sorted({n for n in [name, *labels] if n}),
        input_hash=input_hash(context),
        context=context,
    )


_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_NON_ALNUM = re.compile(r"[^0-9a-z]+")


def _normalize(text: str) -> str:
    return " " + _NON_ALNUM.sub(" ", text.lower()).strip() + " "


def _mentions(query: str, names: List[str]) -> bool:
    padded = _normalize(query)
    for name in names:
        norm = _normalize(name).strip()
        if len(norm) >= 3 and f" {norm} " in padded:
            return True
    return False


def parse_queries(raw: str, names: List[str]) -> Optional[List[str]]:
    """
    The usable queries in an LLM answer, or None when the answer cannot be parsed.

    An empty list is a valid answer ("not enough information"); None is a failure
    and is not stored, so the tool is retried on the next run. Queries outside the
    word bounds, naming the tool, or repeating another are dropped.
    """
    if not raw:
        return None
    text = _THINK.sub("", raw).strip()
    start, end = text.find("{"), text.rfind("}")
    candidates = []
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    list_start, list_end = text.find("["), text.rfind("]")
    if list_start != -1 and list_end > list_start:
        candidates.append(text[list_start : list_end + 1])

    parsed: Any = None
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            break
        except json.JSONDecodeError:
            continue
    if isinstance(parsed, dict):
        parsed = parsed.get("queries")
    if not isinstance(parsed, list):
        return None

    queries: List[str] = []
    seen: set[str] = set()
    for item in parsed:
        if not isinstance(item, str):
            continue
        query = " ".join(item.split()).strip(" .")
        key = _normalize(query)
        if (
            not (MIN_WORDS <= len(query.split()) <= MAX_WORDS)
            or _mentions(query, names)
            or key in seen
        ):
            continue
        seen.add(key)
        queries.append(query)
    return queries[:MAX_QUERIES]


def result_from_completion(request: QueryRequest, raw: str) -> Optional[QueryResult]:
    """Turn an LLM answer into a result; None when it has to be retried."""
    queries = parse_queries(raw, request.names)
    if queries is None:
        return None
    if not queries:
        return QueryResult(STATUS_INSUFFICIENT)
    return QueryResult(STATUS_GENERATED, queries)


def build_document(
    request: QueryRequest, result: QueryResult, model: Optional[str], now: str
) -> dict:
    """The `semantic_search` document for one tool."""
    return {
        "tool_id": request.tool_id,
        "tool_name": request.tool_name,
        "status": result.status,
        "queries": result.queries,
        "input_hash": request.input_hash,
        "prompt_version": request.prompt_version,
        "model": model,
        "generated_at": now,
    }


def is_current(request: QueryRequest, stored: Optional[dict]) -> bool:
    """Whether the stored document was generated from exactly this input and prompt."""
    return (
        stored is not None
        and stored.get("input_hash") == request.input_hash
        and stored.get("prompt_version") == request.prompt_version
    )
