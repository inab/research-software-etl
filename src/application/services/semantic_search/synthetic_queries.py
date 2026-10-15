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
from collections import Counter
from typing import Any, Iterable, List, Optional

# Bump when a prompt or build_tool_context change in a way that should
# regenerate every tool's queries.
PROMPT_VERSION = "1"
# Version 2 adds an excerpt of the tool's GitHub README to the context. Opt-in
# here (build_request(..., prompt_version=README_PROMPT_VERSION)); the
# `rsetl synthetic-queries` CLI defaults to it and fetches the READMEs.
README_PROMPT_VERSION = "2"

MAX_QUERIES = 6
MIN_WORDS = 3
MAX_WORDS = 15
MAX_DESCRIPTION_CHARS = 2000
MAX_README_CHARS = 3000
# A word in the descriptions of at least this many tools is vocabulary, not an
# identifier (see `vocabulary`). Chosen on the 2026-10 corpus (~50k tools):
# "driver" (91), "partition" (58) and "word"/"cloud" clear it; one-off names
# such as "brinda" or "trvae" (1 each) are nowhere near.
MIN_VOCABULARY_DF = 50

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

# What `vocabulary` reads: the descriptions, and the help text they fall back to.
VOCABULARY_PROJECTION = {"_id": 1, "data.description": 1, "data.documentation": 1}

# What `readme_repos` reads.
README_REPO_PROJECTION = {"_id": 1, "data.repository": 1}

_GITHUB_REPO = re.compile(r"github\.com[/:]([^/\s#?]+)/([^/\s#?]+)", re.IGNORECASE)

_README_RULE = """
- The record may end with an excerpt of the tool's README. Use it for specifics \
(data types, file formats, methods, organisms, use cases); ignore installation \
steps, licensing, citation, badges and other boilerplate.
- Do not base queries on example datasets, benchmark figures, version numbers or \
implementation internals (encodings, checksums, internal file layouts): \
researchers search for what a tool does, not for how it was tested or built."""

# Version 2 also steers towards the length people actually type.
_README_LENGTH = ", mostly 4-10, as a researcher would type them"


def _system_prompt(readme_rule: str = "", length_hint: str = "") -> str:
    return f"""You write search queries that researchers would type into a \
life-science research software registry to find a specific tool.

Given a tool record, write up to {MAX_QUERIES} diverse queries ({MIN_WORDS}-{MAX_WORDS} \
words each{length_hint}) for which this tool is a strong, specific answer.

Rules:
- Phrase each query as a researcher's need: the task, the data types, the file \
formats, the organisms, the method or the domain, stated concretely.
- Vary the angle across queries (task, input data, output, domain, method); do not \
paraphrase the same query.
- Never include the tool's name or label.
- No generic queries such as "bioinformatics tool", "data analysis software" or \
"process files".
- Use only information present in the record; do not invent capabilities.{readme_rule}
- If the record lacks enough specific information to write useful queries, return \
an empty list.

Respond with JSON only, no commentary: {{"queries": ["...", "..."]}}"""


SYSTEM_PROMPT = _system_prompt()
SYSTEM_PROMPTS = {
    PROMPT_VERSION: SYSTEM_PROMPT,
    README_PROMPT_VERSION: _system_prompt(_README_RULE, _README_LENGTH),
}


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
            {"role": "system", "content": SYSTEM_PROMPTS[self.prompt_version]},
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


# README sections that say nothing about what a tool is for.
_BOILERPLATE_HEADING = re.compile(
    r"\b(install\w*|licen[cs]es?|licensing|citations?|citing|cite|contribut\w*|"
    r"acknowledge?ments?|changelog|change log|news|funding|contacts?|support|"
    r"authors?|maintainers?|table of contents|contents|badges?|requirements|"
    r"prerequisites|dependencies|download\w*|docker|conda|bioconda|setup|compil\w*|"
    r"building|getting help|issues|bugs|copyright|tests?|testing|development|"
    r"developers?|benchmarks?|benchmarking|performance|roadmap|release notes|"
    r"documentation)\b",
    re.IGNORECASE,
)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_FENCE = re.compile(r"^(```|~~~).*?^\1[^\n]*$", re.DOTALL | re.MULTILINE)
_BADGE = re.compile(r"\[!\[[^\]]*\]\([^)]*\)\]\([^)]*\)")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_LINK_DEF = re.compile(r"^\s*\[[^\]]+\]:\s*\S+.*$", re.MULTILINE)
_HTML_TAG = re.compile(r"<[^>]+>")
# reStructuredText: `text <url>`_ links, `text`_ / name_ references, |substitutions|.
_RST_LINK = re.compile(r"`([^`<]*?)\s*(?:<[^>]*>)?`_{1,2}")
_RST_REF = re.compile(r"\b(\w+)_(?=[\s.,;:)]|$)", re.MULTILINE)
_RST_SUBST = re.compile(r"\|[\w -]+\|")
# Explicit markup (directives, link targets, comments) and directive options.
_RST_DIRECTIVE = re.compile(r"^\s*(\.\.\s|:\w[\w -]*:\s).*$", re.MULTILINE)
_UNDERLINE_LEVEL = {"=": 1, "-": 2, "~": 3, "^": 4}
_ATX = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
# A line that is only markup: setext/RST underlines, table rules, separators.
_RULE = re.compile(r"^[\s=\-~*_|:+^#`]*$")


def clean_readme(text: Optional[str]) -> Optional[str]:
    """
    A README reduced to the prose that says what the tool does, or None.

    Drops code blocks, images and badges, HTML, link targets (keeping link text),
    and whole sections whose heading is boilerplate (installation, licence,
    citation, ...). Capped at MAX_README_CHARS, cut at a line boundary.
    """
    if not text:
        return None
    for pattern, repl in (
        (_HTML_COMMENT, ""),
        (_FENCE, ""),
        (_BADGE, ""),
        (_IMAGE, ""),
        (_LINK, r"\1"),
        (_LINK_DEF, ""),
        (_RST_LINK, r"\1"),
        (_RST_REF, r"\1"),
        (_RST_SUBST, ""),
        (_HTML_TAG, ""),
        (_RST_DIRECTIVE, ""),
    ):
        text = pattern.sub(repl, text)

    lines: List[str] = []
    skip_level: Optional[int] = None
    in_literal = False
    raw = text.splitlines()
    for n, line in enumerate(raw):
        line = line.rstrip()
        # An RST literal block (code): the indented lines after one ending in "::".
        if in_literal:
            if not line or line[0].isspace():
                continue
            in_literal = False
        if line.endswith("::"):
            in_literal = True
            line = line[:-1].rstrip(":").rstrip() + ":" if line.strip() != "::" else ""
        heading = _ATX.match(line)
        level, title = (
            (len(heading.group(1)), heading.group(2)) if heading else (None, None)
        )
        # Setext / RST heading: a text line underlined with one of these.
        nxt = raw[n + 1].strip() if n + 1 < len(raw) else ""
        if not heading and line.strip() and len(nxt) >= 3 and len(set(nxt)) == 1:
            level = _UNDERLINE_LEVEL.get(nxt[0])
            title = line.strip() if level else None
        if title is not None:
            if skip_level is not None and level <= skip_level:
                skip_level = None
            if skip_level is None and _BOILERPLATE_HEADING.search(title):
                skip_level = level
                continue
        if skip_level is not None:
            continue
        if _RULE.match(line):
            if lines and lines[-1]:
                lines.append("")
            continue
        lines.append(heading.group(2) if heading else line)

    out: List[str] = []
    size = 0
    for line in "\n".join(lines).strip().splitlines():
        if size + len(line) + 1 > MAX_README_CHARS:
            break
        out.append(line)
        size += len(line) + 1
    cleaned = "\n".join(out).strip()
    return cleaned or None


def github_repos(tool: dict) -> set[tuple[str, str]]:
    """The tool's GitHub repositories as (owner, repo), lowercased, without .git."""
    found = set()
    for item in (tool.get("data") or {}).get("repository") or []:
        url = item.get("url") if isinstance(item, dict) else None
        match = _GITHUB_REPO.search(url or "")
        if match:
            repo = re.sub(r"\.git$", "", match.group(2), flags=re.IGNORECASE)
            found.add((match.group(1).lower(), repo.lower()))
    return found


def readme_repos(tools: Iterable[dict]) -> dict[str, tuple[str, str]]:
    """
    tool_id -> the GitHub repository whose README describes the tool.

    Only tools with exactly one GitHub repository that no other tool shares: a
    hub repository's README describes the hub, not the tool (ucscgenomebrowser/kent
    backs 171 tools). ``tools`` must be the whole collection
    (``README_REPO_PROJECTION``), or sharing goes unnoticed.
    """
    per_tool = {str(tool["_id"]): github_repos(tool) for tool in tools}
    per_repo = Counter(repo for found in per_tool.values() for repo in found)
    sole = {k: next(iter(found)) for k, found in per_tool.items() if len(found) == 1}
    return {k: repo for k, repo in sole.items() if per_repo[repo] == 1}


def build_tool_context(data: dict, readme: Optional[str] = None) -> Optional[str]:
    """
    The record as the LLM sees it, or None when there is nothing to go on.

    None means no description, no help text, no EDAM topics or operations and no
    README -- a name alone is not enough to write specific queries. Anything more goes to
    the LLM, which makes the final call: short Galaxy descriptions ("In aligned
    Bam files.") read fine next to the name ("bbtools_callvariants").

    ``readme`` is an already-cleaned README excerpt (``clean_readme``); it goes
    last, after the curated fields.
    """
    descriptions = _descriptions(data)
    topics = _terms(data.get("topics"))
    operations = _terms(data.get("operations"))
    if not descriptions and not topics and not operations and not readme:
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
    if readme:
        lines.append("README (excerpt):\n" + readme)
    return "\n".join(lines)


def input_hash(context: Optional[str]) -> str:
    """
    Fingerprint of what the LLM is shown.

    Deliberately not the tool's `content_hash`: that changes whenever a version or
    download URL does, which says nothing about what the tool is for.
    """
    return hashlib.sha256((context or "").encode("utf-8")).hexdigest()


def _tokens(text: str) -> List[str]:
    return [t for t in _NON_ALNUM.split(text.lower()) if len(t) >= 3]


def vocabulary(
    tools_data: Iterable[dict], min_df: int = MIN_VOCABULARY_DF
) -> frozenset:
    """
    Words used in the descriptions of at least ``min_df`` tools.

    The name filter (``_mentions``) exists to stop queries that just repeat the
    tool's name. A name made only of such words ("driver", "word_cloud", a label
    like "Filter") is how the field describes the task, and filtering it drops
    exactly the tool's most relevant queries ("prioritize cancer driver genes").
    The price: a few tools so widely cited that their name is vocabulary too
    ("samtools", "blast") may keep it in a query.
    """
    df: Counter = Counter()
    for data in tools_data:
        df.update(set(_tokens(" ".join(_descriptions(data or {})))))
    return frozenset(word for word, n in df.items() if n >= min_df)


def _is_vocabulary(name: str, vocab: frozenset) -> bool:
    tokens = _tokens(name)
    return bool(tokens) and all(t in vocab for t in tokens)


def build_request(
    tool: dict,
    readme: Optional[str] = None,
    prompt_version: str = PROMPT_VERSION,
    vocab: frozenset = frozenset(),
) -> QueryRequest:
    """
    One tool's prompt. ``readme`` is the raw README text; it is cleaned here and
    used only by a prompt version that knows about it. Names made only of words
    in ``vocab`` (see ``vocabulary``) do not filter queries.
    """
    data = tool.get("data") or {}
    name = data.get("name") or ""
    labels = [label for label in data.get("label") or [] if isinstance(label, str)]
    if prompt_version not in SYSTEM_PROMPTS:
        raise ValueError(f"Unknown prompt version: {prompt_version}")
    if prompt_version != README_PROMPT_VERSION:
        readme = None
    context = build_tool_context(data, clean_readme(readme))
    return QueryRequest(
        tool_id=str(tool["_id"]),
        tool_name=name,
        names=sorted(
            {n for n in [name, *labels] if n and not _is_vocabulary(n, vocab)}
        ),
        input_hash=input_hash(context),
        context=context,
        prompt_version=prompt_version,
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
