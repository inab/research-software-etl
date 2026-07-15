# NOTE:
# The webAvailability collection was initially populated from a broader dataset
# that included both relevant (web-based/deployable) and non-relevant (cmd, etc)
# URL records (from OEB tools monitoring). Because some of the non-relevant
# records could still have future value, they were not removed.
#
# Instead, relevance is modeled explicitly through the `is_relevant` flag. This
# makes it possible to preserve the full imported dataset while restricting the
# daily monitoring workflow to the subset of URLs that correspond to relevant
# tool webpages.
#
# ---> This use case was used once and is not meant to be executed periodically

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Set

from domain.repositories import Repositories


RELEVANT_TYPES = {"rest", "web", "app", "suite", "workbench", "db", "soap", "sparql"}


def now_iso_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_http_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(("http://", "https://"))


@dataclass(frozen=True)
class TagRelevantWebAvailabilityConfig:
    """
    The knobs for one run of the stage.

    Collection names are not among them: they live in `PipelineConfig`, and the
    repositories this use case is handed already point at the right ones.
    """

    created_by: str = "oeb-ingest"
    updated_by: str = "oeb-ingest"
    bulk_chunk: int = 500
    batch_size: int = 200
    limit_tools: int = 0  # 0 = all
    dry_run: bool = False


@dataclass(frozen=True)
class TagRelevantWebAvailabilityResult:
    tools_scanned: int
    tools_matched: int
    relevant_urls_found: int
    upserts_sent: int


def run_tag_relevant_webavailability_urls(
    cfg: TagRelevantWebAvailabilityConfig, repos: Repositories
) -> TagRelevantWebAvailabilityResult:
    """
    Tag (and upsert) web-availability docs based on the tools collection:
    - If tool.data.type intersects RELEVANT_TYPES, then every URL in tool.data.webpage
      is relevant.
    - For each relevant URL, upsert a web-availability doc with empty availability on
      insert.
    - The `is_relevant` tag is set to True (top-level).
    """

    # 1) Collect relevant URLs from the tools collection
    relevant_urls: Set[str] = set()
    tools_scanned = 0
    tools_matched = 0

    for tool in repos.tools.iter_projected(
        query={},
        projection={"data.type": 1, "data.webpage": 1},
        limit=cfg.limit_tools,
        batch_size=cfg.batch_size,
    ):
        tools_scanned += 1
        data = tool.get("data") or {}
        types = data.get("type")

        if not isinstance(types, list):
            continue

        if not any(isinstance(t, str) and t in RELEVANT_TYPES for t in types):
            continue

        tools_matched += 1
        webpages = data.get("webpage")

        if isinstance(webpages, list):
            relevant_urls.update(u.strip() for u in webpages if _is_http_url(u))

    if not relevant_urls:
        return TagRelevantWebAvailabilityResult(
            tools_scanned=tools_scanned,
            tools_matched=tools_matched,
            relevant_urls_found=0,
            upserts_sent=0,
        )

    # 2) Upsert + tag into the web-availability collection
    upserts_sent = 0
    if not cfg.dry_run:
        upserts_sent = repos.web_availability.tag_relevant(
            urls=sorted(relevant_urls),
            source=repos.tools.collection_name,
            tagged_at=now_iso_z(),
            created_by=cfg.created_by,
            updated_by=cfg.updated_by,
            log_label="tag-relevant-urls",
            chunk_size=cfg.bulk_chunk,
        )
    else:
        upserts_sent = len(relevant_urls)

    return TagRelevantWebAvailabilityResult(
        tools_scanned=tools_scanned,
        tools_matched=tools_matched,
        relevant_urls_found=len(relevant_urls),
        upserts_sent=upserts_sent,
    )
