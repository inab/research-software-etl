# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

ETL pipeline that consolidates, deduplicates, and enriches metadata for research software in the life sciences. It pulls records from multiple registries (ToolShed, Bioconductor, Galaxy, BioTools, etc.), normalizes them, detects and resolves conflicts, calculates FAIRness scores, and stores the result in MongoDB.

## Commands

**Installation:**
```bash
pip install -e .           # standard install
pip install -e ".[dev]"    # with dev dependencies (black, ruff, mypy, pytest)
pip install -e ".[docs]"   # with mkdocs dependencies
```

**Run the pipeline:**
```bash
rsetl run                                  # full integration pipeline
rsetl run --from-stage <stage>             # start from a specific stage
rsetl run --until <stage>                  # run up to and including a stage
rsetl run --only <stage>                   # run exactly one stage
rsetl run --resume-run <run_id_or_path>    # resume a previous run
rsetl run --tag <label>                    # tag this run for identification
rsetl run --dry-run-disambiguation         # disambiguation without creating GitHub issues
rsetl check-env                            # validate env vars and API connectivity
rsetl runs list / show <id> / latest       # inspect past runs
```

**Tests:**
```bash
pytest                   # all tests (excludes @manual)
pytest -m manual         # only manual tests (require full env setup)
pytest tests/path/file.py::TestClass::test_name   # single test
pytest --cov             # with coverage
```

**Linting / formatting:**
```bash
black src/ tests/        # format
ruff check src/ tests/   # lint
mypy src/                # type check
```

**Docs:**
```bash
mkdocs serve             # local preview at http://127.0.0.1:8000
mkdocs build             # static build
```

## Architecture

Clean architecture with four layers: `adapters` → `application` → `domain` → `infrastructure`.

```
src/
├── adapters/cli/          # CLI entry points (Typer); one subcommand per major stage group
├── application/
│   ├── use_cases/         # Orchestrates sequences of services for each pipeline stage
│   └── services/          # Domain logic: grouping, conflict detection, disambiguation, FAIR scoring
├── domain/models/         # Pydantic models: PretoolsEntryModel, ToolEntryModel, PublicationEntryModel
└── infrastructure/
    ├── db/mongo/          # MongoDB adapter + repositories (raw, standardized, publications)
    ├── storage/           # JSONL/JSON file I/O for inter-stage data
    └── external/          # API clients (Europe PMC, Semantic Scholar, OpenRouter)
```

**Pipeline stages (in order):**

1. **Transformation** — fetch raw entries from MongoDB source collections, standardize to `PretoolsEntryModel`, write to `pretools` collection
2. **License normalization** — map license strings to SPDX identifiers
3. **Grouping & recovery** — cluster related records by repo URL and name; recover entries shared across groups
4. **Remove OEB metrics** (optional) — drop low-information OpenEBench metrics
5. **Conflict detection** — find duplicates/inconsistencies within groups
6. **Simplification** — reduce block complexity
7. **JSON→JSONL conversion** — prepare for downstream processing
8. **Disambiguation** — resolve conflicts via heuristics and LLM-assisted scoring; ambiguous cases create GitHub issues for curators
9. **Human updates** (optional) — apply curator decisions stored as Git annotations
10. **Merge** — produce the final tool entries, carrying each one's `_id` over from the run before, and promote them into the `tools` collection (see *Tool identity* below)
11. **Reindex** — ask the observatory API to rebuild the `tools` collection's search/filter indexes. Merge promotes a freshly-built collection that has only its `_id` index, so `/search` is broken until this runs (see *Tool indexes* below). Skipped when merge is (`--no-merge`); coupled to it in `_resolve_selected_stages`
12. **FAIRsoft scores** — calculate FAIR compliance metrics per tool (via the `fairsoft-core` engine). Incremental by default: `fair_scores` only scores tools whose `last_updated_at` falls within `--updated-within-days` (default 30), mirroring the transformation stage. `--updated-within-days 0` scores every tool. This works because merge only bumps a tool's `last_updated_at` when its content actually changed (see *Tool identity*)
13. **Statistics** — aggregate metrics for visualization

**Run management:** Each execution creates a timestamped directory under `data/integration/runs/<YYYYMMDDTHHMMSSZ-<git_sha>[-tag]>/` with a `manifest.json` tracking stage inputs, outputs, and completion state. `--resume-run` uses this manifest to skip completed stages. `data/integration/runs/latest` symlinks to the most recent run.

**Key patterns:**
- `DatabaseAdapter` is a Protocol; all database access goes through typed repositories rather than raw pymongo calls
- Each entry has a `@metadata` dict (provenance, source) alongside its `data` payload
- Large collections are processed in batches via generators to avoid loading everything into memory
- All credentials and API tokens come from `.env` (MongoDB URI, GitHub, GitLab, OpenRouter, HuggingFace)
- Tests use `.env` auto-loading; tests requiring a live environment are marked `@pytest.mark.manual`

**Configuration (`src/infrastructure/config.py`):**

Collection names and file paths live in `PipelineConfig`; API tokens live in `Credentials`; CI provenance lives in `CIContext`. Nothing below `adapters/` reads the environment.

Each stage CLI builds the config once, from env vars plus its own argv, and passes it down:

```python
config = PipelineConfig.from_env(grouped_json_path=args.grouped_entries_file)
grouping_and_recovery_process(config)
```

`run_full` executes each stage as a *subprocess*, so config is constructed once per stage process, not once per pipeline. Env vars and CLI flags are how the orchestrator talks to stages.

- Adding a path or collection name? Add a field to `PipelineConfig` — do not inline a literal.
- `Credentials` is kept separate from `PipelineConfig` so tokens can't ride along into logs or the run manifest; its `__repr__` is redacted.

**Database access (`src/infrastructure/db/`):**

Application code never names a collection or calls a Mongo verb. It receives a `Repositories` bundle — the database's counterpart to `ExternalClients` — and asks a repository for what it wants:

```python
config = PipelineConfig.from_env(...)
repos = Repositories.from_config(config)   # built once, at the CLI
grouping_and_recovery_process(config, repos)
```

`Repositories.from_config` wires every repository (`alambique`, `pretools`, `tools`, `tools_staging`, `publications`, `license_mapping`, `computations`, `similarities`, `web_availability`) over one adapter. Building it is free: `MongoDBAdapter` keeps its pymongo client in a *class* attribute and connects on first use, so each stage subprocess wires its own without multiplying connections.

Use cases take the whole `Repositories` bundle; services take the one narrow repository they need (`count_types_tools(tools, tag, computations)`), so a service's signature says exactly which collections it can touch.

- Need a new query? Add a method to the repository, not a `fetch_entry` call in `application/`.
- Need a new collection? Add a field to `PipelineConfig` and a slot to `Repositories`.
- Driver types stay in `infrastructure/`. `WebAvailabilityRepository` builds its own `pymongo.UpdateOne`s; callers pass plain dicts. `tests/test_architecture.py` fails the build if `pymongo` is imported anywhere under `application/`.
- `DatabaseAdapter` (`infrastructure/db/database_adapter.py`) is satisfied *structurally* — concrete adapters must not inherit from it. It used to be inherited, and because its method bodies are `pass`, a method the adapter didn't implement returned `None` instead of raising.

**Tool identity (`src/application/services/integration/tool_identity.py`):**

A tool's `_id` must outlive the run that produced it: FAIR scores upsert on `computationsDev.createdFrom = [str(tool._id)]`, and the front-end looks tools up by `similaritiesDev.tool_id`. Merge used to insert documents with no `_id`, so MongoDB minted a new one every run and every one of those references went stale.

A tool's lineage is its `source` list — the pretools entries it was merged from. Each newly merged tool inherits the `_id` of the previous tool it shares the most lineage with. Ordering (`previous.created_at ASC, previous._id ASC, overlap DESC, block_key ASC`) makes two rules fall out: when several tools collapse into one, the **oldest** id survives; when one tool splits, the **dominant** successor keeps it. `assign_identities` is pure and total — no database, no dependence on iteration order.

A tool document carries two timestamps named to match pretools: `created_at` (set once, when the tool first appears, and carried forward by every successor) and `last_updated_at` (the last merge that changed its content — see *Content fingerprint* below). These replaced the earlier `first_seen` / `timestamp` fields; `previous_tool_from_document` still reads the old names so a collection written before the rename carries its dates across the first post-rename run. The tool `source` field is lineage (a list of pretools ids), unrelated to pretools' own `source`.

Merge therefore cannot write into the live collection: it is what the new entries inherit from. It builds into `tools_staging` (`toolsDev_next`), then `finalize_run` archives the live collection as `toolsDev_archive_<run_id>` and promotes staging in its place — two atomic renames. `rsetl rollback <run_id>` reverses it. Use `--no-promote` to build the staging collection without swapping it in.

The merge stage prints `preserved / new / retired / contested`. **`contested` is the number to watch**: it counts tools where the oldest ancestor won over one that shared more lineage. If it is not near zero on a real run, the ordering above deserves a second look.

**Content fingerprint (change detection).** A tool's update time used to be set to `now()` on every merge, so it was a "this run touched it" marker, not a "content changed" one — which made the FAIR stage (keyed on it) recompute every tool every run. Merge now stores a `content_hash` on each tool (`content_hash` in `tool_identity.py`: an order-insensitive fingerprint of `data`, because the merge validators call `list(set(...))` and list order is not stable run to run). When a merged tool's hash matches the ancestor it continues, it **keeps the ancestor's `last_updated_at`**; only genuinely changed tools get a fresh one. That is what makes incremental FAIR (above) correct. Caveat: the hash covers a tool's own `data` (including its publication id list), not the contents of the linked publication documents — a publication whose metadata changes without any change to the tool will not bump the tool's `last_updated_at`.

**Tool indexes (the `reindex` stage).** Promotion renames the old `tools` collection to the archive (which *keeps* its indexes — `renameCollection` preserves them) and swaps in the staging collection merge built by plain inserts, so the live collection is left with only its `_id` index. That breaks the API's `/search` (`text index required for $text query`) and turns filtered searches into collection scans. The index *definitions* live in the API repo (they encode its query shapes and a collation that must match the search route), so the pipeline does not own them: the `reindex` stage (`adapters/cli/integration/reindex.py`) POSTs to the API's admin reindex endpoint via `ObservatoryApiClient`, and the API rebuilds them. It runs right after merge, and only when merge does (skipped under `--no-merge`). Rollback needs no reindex — it restores the archive, indexes and all. Two failure rules: a missing `OBSERVATORY_ADMIN_TOKEN` is checked *before* merge runs (in `run_full`) so a misconfig can't promote a collection it then can't reindex; an API call that fails at run time only *warns and exits 0*, because the collection is already live and the API re-ensures indexes on its next restart anyway.

**External API clients (`src/infrastructure/external/`):**

**Every HTTP call the pipeline makes lives here**, behind a client class — not just the tokened ones. `ExternalClients.from_credentials(creds)` bundles them, and the CLI threads that bundle down the disambiguation chain (`run_full_disambiguation → disambiguate_blocks → process_conflict → {proxy, conflict_builder → enrich_links}`).

- Tokened, each holding its token as a constructor argument: `GitHubClient`, `GitLabClient`, `OpenRouterClient`, `HuggingFaceClient`.
- Tokenless, bundled for the same reason — a service that owns a `requests.Session` cannot be run offline: `UrlChecker`, `PyPIClient`, `SourceForgeClient` (Cloudflare retry/backoff), `BitbucketClient`, `HeadlessBrowserFetcher` (Playwright).
- Built directly by the CLI that needs them, not bundled: `EuropePmcClient`, `SemanticScholarClient`, `CrossrefClient` (its `mailto` is a CLI flag, not a credential), and `ObservatoryApiClient` (tokened with `OBSERVATORY_ADMIN_TOKEN`, used only by the `reindex` stage — see *Tool indexes* above).

`UrlChecker` is the "is this URL reachable, and where does it end up?" seam: `probe()` (HEAD, falling back to GET) for the web-availability stage, `resolve_redirects()` for GitHub redirect resolution in conflict detection and for link enrichment. Those three each owned a `requests.Session` before, so none of them could run without a network.

No module under `application/` may read a token, build an `Authorization` header, or make an HTTP request. Services receive `clients` (or the one narrow client they need — `run_update_web_availability_daily(cfg, repos, url_checker)`) and call methods on it. `tests/test_architecture.py` fails the build if `requests`, `httpx`, `playwright` or `urllib.request` is imported under `application/` or `domain/`.

Tests inject fakes into `ExternalClients` rather than patching module globals — see `tests/application/services/integration/test_agreement_proxy.py`. `fake_clients()` leaves the four tokened slots `None` (so an unexpected reach-through raises) but fills the tokenless fetchers with offline fakes, so no test can reach the network by forgetting one. That is not hypothetical: while the disambiguation tests patched `enrich_links.get_link_content`, the redirect check underneath it went unpatched and hit the live network on every conflict.

**Tests:**

`pytest` runs green offline: no MongoDB, no API keys, no network. Two rules keep it that way.

1. **Inject fakes; don't patch.** `tests/fakes.py` has `FakeDatabaseAdapter` (in-memory, implements the `DatabaseAdapter` protocol), `fake_repos()`, `FakeGitHubClient` and `fake_clients()`. Build a `Repositories`/`ExternalClients` out of fakes and pass it in. `fake_repos()` wires only the collections you ask for, so a use case reaching for one you didn't wire raises instead of appearing to work.
2. **Patch targets must not be prefixed with `src.`** The package installs as `application.*`, so `monkeypatch.setattr("src.application...")` patches a *different module object* and silently patches nothing — the real function then runs against the real API or database. Several tests carried this bug: they were hitting live LLM endpoints and would have opened real GitHub issues.
3. **`@pytest.mark.manual` is a last resort**, for what genuinely cannot be faked (excluded by `addopts = -m "not manual"`; run them with `pytest -m manual`). It is not free: while the disambiguation tests were manual, nobody ran them, and they silently rotted — their expected values had drifted from the code in two places. If you mark a test manual, you are choosing not to run it.

Test modules are packages (`tests/**/__init__.py`): two `test_disambiguation.py` files exist in different directories, and without `__init__.py` pytest imports both by bare basename and they collide. `pytest.ini` sets `testpaths = tests` so the vendored legacy `FAIRsoft/` tree is not collected.

`tests/test_architecture.py` enforces the two layering rules below — it will fail the build, so read it before working around it.

**Known architectural debt — do not make it worse:**
- There is no mongo singleton any more: `mongo_db_singleton.py` is deleted, and every stage — the core pipeline, `stats_generation` and `web_availability` alike — takes a `Repositories` argument. Do not build a `MongoDBAdapter()` below `adapters/` to get around it; `tests/test_architecture.py` fails the build if you do. (The one-off scripts under `scripts/` construct their own adapter, and are outside these rules.)
- Do not add new `os.getenv` calls below `adapters/` — read config once at the CLI layer via `PipelineConfig.from_env()` and pass it down.
- `build_disambiguated_record`'s zero-pair branch and `build_no_conflict_record` describe the same situation differently — one labels it `no_conflict` without the "different names" caution, the other `merged` with it. Harmless downstream (`merge_entries` treats both labels alike), but they should agree.
- A stage must not write into the working tree. The disambiguation chain (`run_full_disambiguation → disambiguate_blocks → process_conflict → run_second_round`) takes the `PipelineConfig` the CLI built and gets **every** path from it — inputs, the disambiguated-blocks output, the pair-decision cache, and the proxy diagnostics, which `run_full` points at `data/integration/runs/<run_id>/results_proxy.<run_id>.jsonl`. It used to construct a `PipelineConfig()` *inline*, whose defaults are relative to the repository root, so a run appended to tracked files instead (`scripts/data/results_proxy.jsonl` is 10k lines of committed residue from exactly that). Do not reintroduce an inline `PipelineConfig()` in a service that writes.
  - Two read-only fallbacks remain and are harmless: the GitHub issue *template* in `issues.py` and the repository blacklist in `group_entries.py`, both checked-in inputs.
  - `pair_decisions_path` is deliberately **not** run-scoped: it is the curator decision history and accumulates across runs.
