"""
Central configuration for the ETL pipeline.

Every value the pipeline reads from the environment or would otherwise hardcode
as a relative path lives here. Configuration is read from the environment
exactly once, at the CLI layer (``adapters/cli/*``), and passed down explicitly:
use cases and services receive a ``PipelineConfig`` (and, where needed, a
``Credentials``) instead of calling ``os.getenv`` or opening literal paths.

The pipeline orchestrator runs each stage as a separate subprocess, so "once"
means once per stage process -- each stage CLI builds its own config from the
environment plus its own command-line arguments. Nothing below ``adapters/``
touches the environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any, Optional


def _env_path(name: str, default: str) -> Path:
    return Path(os.getenv(name, default))


@dataclass(frozen=True)
class CIContext:
    """
    Provenance of the run, as reported by the CI environment.

    Recorded on every entry's ``@metadata`` so a stored record can be traced
    back to the commit and pipeline that produced it. All fields are absent
    when running locally.
    """

    pipeline_url: Optional[str] = None
    project_namespace: Optional[str] = None
    project_name: Optional[str] = None
    commit_sha: Optional[str] = None

    # Used when a local run has no CI commit to point at.
    fallback_commit_url: str = (
        "https://gitlab.com/evamdpico/research-software-meta/-/tree/"
        "4a4cdc3c2076f6f7c920c5de93d9d2563ec5bcba"
    )

    @classmethod
    def from_env(cls) -> "CIContext":
        return cls(
            pipeline_url=os.getenv("CI_PIPELINE_URL"),
            project_namespace=os.getenv("CI_PROJECT_NAMESPACE"),
            project_name=os.getenv("CI_PROJECT_NAME"),
            commit_sha=os.getenv("CI_COMMIT_SHA"),
        )

    def commit_url(self) -> str:
        """URL of the commit that produced this run, or a local-run fallback."""
        if not (self.project_namespace and self.project_name and self.commit_sha):
            return self.fallback_commit_url
        return (
            f"https://gitlab.bsc.es/{self.project_namespace}/"
            f"{self.project_name}/-/commit/{self.commit_sha}"
        )

    def logs_url(self) -> str:
        """URL of the CI job logs, or ``"local"`` outside CI."""
        return self.pipeline_url or "local"


class MissingCredentialError(RuntimeError):
    pass


@dataclass(frozen=True)
class Credentials:
    """
    API tokens, kept out of :class:`PipelineConfig` on purpose.

    ``PipelineConfig`` is logged and serialized into the run manifest; tokens
    must not ride along into those. ``__repr__`` is redacted so a stray print
    or a traceback frame cannot leak a token.
    """

    github_token: Optional[str] = None
    gitlab_token: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Credentials":
        return cls(
            github_token=os.getenv("GITHUB_TOKEN"),
            gitlab_token=os.getenv("GITLAB_TOKEN"),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
            huggingface_api_key=os.getenv("HUGGINGFACE_API_KEY"),
        )

    def require(self, *names: str) -> "Credentials":
        """Fail fast, at the CLI, if a stage's required tokens are absent."""
        missing = [n for n in names if not getattr(self, n)]
        if missing:
            raise MissingCredentialError(
                "Missing required credentials: "
                + ", ".join(sorted(n.upper() for n in missing))
            )
        return self

    def __repr__(self) -> str:
        shown = ", ".join(
            f"{f.name}={'<set>' if getattr(self, f.name) else '<unset>'}"
            for f in fields(self)
        )
        return f"Credentials({shown})"


@dataclass(frozen=True)
class PipelineConfig:
    """
    Collections and file paths for one stage process.

    Built once per process by a CLI entrypoint via :meth:`from_env`, which
    layers command-line overrides on top of environment variables on top of the
    defaults below.
    """

    # --- MongoDB collections ---
    # NB: publications_collection defaults to the name the repository actually
    # used ("publicationsMetadataDev"), not the "publicationsDev" default of the
    # old PUBLICATIONS_COLLECTION constant -- that constant was dead, and
    # honouring it here would silently repoint publication writes.
    alambique_collection: str = "alambiqueDev"
    pretools_collection: str = "pretoolsDev"
    publications_collection: str = "publicationsMetadataDev"
    tools_collection: str = "toolsDev"
    # Merge builds into the staging collection while the live one still serves
    # reads (and still holds the ids the new entries inherit). Finalizing the run
    # archives the live collection and promotes the staging one in its place.
    tools_staging_collection: str = "toolsDev_next"
    tools_archive_prefix: str = "toolsDev_archive_"
    licenses_mapping_collection: str = "licensesMapping"
    computations_collection: str = "computationsDev"
    similarities_collection: str = "similaritiesDev"
    web_availability_collection: str = "webAvailabilityDev"

    # --- Per-run stage artifacts (the orchestrator passes these as CLI flags,
    #     pointing into data/integration/runs/<run_id>/) ---
    grouped_json_path: Path = Path("data/grouped.json")
    conflicts_json_path: Path = Path("data/disconnected.json")
    disambiguated_blocks_path: Path = Path("data/disambiguated_grouped.json")
    # Per-pair proxy verdicts. A diagnostic, but a per-run one: `run_full` points it
    # at the run directory. The default is only for a stage invoked on its own.
    proxy_results_path: Path = Path("data/results_proxy.jsonl")

    # --- Durable, repo-tracked inputs ---
    group_split_corrections_path: Path = Path(
        "data/integration/manual_group_split_corrections.json"
    )
    pair_decisions_path: Path = Path(
        "src/application/services/integration/disambiguation/pair_decisions.jsonl"
    )
    human_log_path: Path = Path("human_annotations/human_conflicts_log.jsonl")
    github_issue_template_path: Path = Path(
        "src/application/services/integration/disambiguation/github_issue.jinja2"
    )
    repo_blacklist_path: Path = Path(
        "scripts/disambiguation/hub_repo_blacklist_over_3_names.txt"
    )

    # Directory (inside the GitHub repo, not on disk) that conflict files for
    # curators are committed to.
    conflicts_repo_dir: Path = Path("human_annotations/conflicts")

    # --- Publication enrichment caches ---
    resolved_dois_path: Path = Path("data/cache/resolved_dois.jsonl")
    unresolved_dois_path: Path = Path("data/cache/unresolved_dois.jsonl")
    publications_enrichment_path: Path = Path(
        "data/cache/publications_enrichment.jsonl"
    )

    # --- Scheduler cadence ---
    # Standard 5-field crontab string, parsed by CronTrigger.from_crontab().
    full_pipeline_cron: str = "0 1 * * mon,thu"  # twice weekly, 01:00 UTC

    ci: CIContext = field(default_factory=CIContext)

    @classmethod
    def from_env(cls, **overrides: Any) -> "PipelineConfig":
        """
        Build a config from the environment, then apply CLI overrides.

        ``None`` overrides are dropped, so a CLI flag that was not supplied
        (argparse default of ``None``) falls through to the environment value
        rather than clobbering it. Path-typed fields accept plain strings.
        """
        cfg = cls(
            alambique_collection=os.getenv("ALAMBIQUE", "alambiqueDev"),
            pretools_collection=os.getenv("PRETOOLS", "pretoolsDev"),
            publications_collection=os.getenv(
                "PUBLICATIONS_COLLECTION", "publicationsMetadataDev"
            ),
            tools_collection=os.getenv("MONGO_TOOLS_COLL", "toolsDev"),
            tools_staging_collection=os.getenv(
                "MONGO_TOOLS_STAGING_COLL", "toolsDev_next"
            ),
            tools_archive_prefix=os.getenv(
                "MONGO_TOOLS_ARCHIVE_PREFIX", "toolsDev_archive_"
            ),
            licenses_mapping_collection=os.getenv(
                "LICENSES_MAPPING", "licensesMapping"
            ),
            computations_collection=os.getenv("COMPUTATIONS", "computationsDev"),
            similarities_collection=os.getenv("SIMILARITIES", "similaritiesDev"),
            web_availability_collection=os.getenv(
                "MONGO_WEBAV_COLL", "webAvailabilityDev"
            ),
            group_split_corrections_path=_env_path(
                "GROUP_SPLIT_CORRECTIONS_FILE",
                "data/integration/manual_group_split_corrections.json",
            ),
            pair_decisions_path=_env_path(
                "PAIR_DECISIONS_FILE",
                "src/application/services/integration/disambiguation/pair_decisions.jsonl",
            ),
            human_log_path=_env_path(
                "HUMAN_ANNOTATIONS_LOG",
                "human_annotations/human_conflicts_log.jsonl",
            ),
            full_pipeline_cron=os.getenv("FULL_PIPELINE_CRON", "0 1 * * mon,thu"),
            ci=CIContext.from_env(),
        )
        return cfg.with_overrides(**overrides)

    def with_overrides(self, **overrides: Any) -> "PipelineConfig":
        known = {f.name for f in fields(self)}
        clean: dict[str, Any] = {}
        for name, value in overrides.items():
            if value is None:
                continue
            if name not in known:
                raise TypeError(f"Unknown PipelineConfig field: {name!r}")
            # Path-typed fields accept strings straight from argparse.
            clean[name] = (
                Path(value) if isinstance(getattr(self, name), Path) else value
            )
        return replace(self, **clean)
