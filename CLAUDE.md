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
11. **FAIRsoft scores** — calculate FAIR compliance metrics per tool
12. **Statistics** — aggregate metrics for visualization

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

`Repositories.from_config` wires every repository (`alambique`, `pretools`, `tools`, `publications`, `license_mapping`) over one adapter. Building it is free: `MongoDBAdapter` keeps its pymongo client in a *class* attribute and connects on first use, so each stage subprocess wires its own without multiplying connections.

- Need a new query? Add a method to the repository, not a `fetch_entry` call in `application/`.
- Need a new collection? Add a field to `PipelineConfig` and a slot to `Repositories`.
- `DatabaseAdapter` (`infrastructure/db/database_adapter.py`) is satisfied *structurally* — concrete adapters must not inherit from it. It used to be inherited, and because its method bodies are `pass`, a method the adapter didn't implement returned `None` instead of raising.

**Tool identity (`src/application/services/integration/tool_identity.py`):**

A tool's `_id` must outlive the run that produced it: FAIR scores upsert on `computationsDev.createdFrom = [str(tool._id)]`, and the front-end looks tools up by `similaritiesDev.tool_id`. Merge used to insert documents with no `_id`, so MongoDB minted a new one every run and every one of those references went stale.

A tool's lineage is its `source` list — the pretools entries it was merged from. Each newly merged tool inherits the `_id` of the previous tool it shares the most lineage with. Ordering (`previous.first_seen ASC, previous._id ASC, overlap DESC, block_key ASC`) makes two rules fall out: when several tools collapse into one, the **oldest** id survives; when one tool splits, the **dominant** successor keeps it. `assign_identities` is pure and total — no database, no dependence on iteration order.

Merge therefore cannot write into the live collection: it is what the new entries inherit from. It builds into `tools_staging` (`toolsDev_next`), then `finalize_run` archives the live collection as `toolsDev_archive_<run_id>` and promotes staging in its place — two atomic renames. `rsetl rollback <run_id>` reverses it. Use `--no-promote` to build the staging collection without swapping it in.

The merge stage prints `preserved / new / retired / contested`. **`contested` is the number to watch**: it counts tools where the oldest ancestor won over one that shared more lineage. If it is not near zero on a real run, the ordering above deserves a second look.

**External API clients (`src/infrastructure/external/`):**

Every call to a tokened third-party API goes through a client class there — `GitHubClient`, `GitLabClient`, `OpenRouterClient`, `HuggingFaceClient` — each holding its token as a constructor argument. `ExternalClients.from_credentials(creds)` bundles them, and the CLI threads that bundle down the disambiguation chain (`run_full_disambiguation → disambiguate_blocks → process_conflict → {proxy, conflict_builder → enrich_links}`).

No module under `application/` may read a token or build an `Authorization` header. Services receive `clients` and call methods on it. Tests inject fakes into `ExternalClients` rather than patching module globals — see `tests/application/services/integration/test_agreement_proxy.py`.

**Tests:**

`pytest` runs green offline: no MongoDB, no API keys, no network. Two rules keep it that way.

1. **Inject fakes; don't patch.** `tests/fakes.py` has `FakeDatabaseAdapter` (in-memory, implements the `DatabaseAdapter` protocol), `fake_repos()`, `FakeGitHubClient` and `fake_clients()`. Build a `Repositories`/`ExternalClients` out of fakes and pass it in. `fake_repos()` wires only the collections you ask for, so a use case reaching for one you didn't wire raises instead of appearing to work.
2. **Patch targets must not be prefixed with `src.`** The package installs as `application.*`, so `monkeypatch.setattr("src.application...")` patches a *different module object* and silently patches nothing — the real function then runs against the real API or database. Several tests carried this bug: they were hitting live LLM endpoints and would have opened real GitHub issues.
3. **`@pytest.mark.manual` is a last resort**, for what genuinely cannot be faked (excluded by `addopts = -m "not manual"`; run them with `pytest -m manual`). It is not free: while the disambiguation tests were manual, nobody ran them, and they silently rotted — their expected values had drifted from the code in two places. If you mark a test manual, you are choosing not to run it.

Test modules are packages (`tests/**/__init__.py`): two `test_disambiguation.py` files exist in different directories, and without `__init__.py` pytest imports both by bare basename and they collide. `pytest.ini` sets `testpaths = tests` so the vendored legacy `FAIRsoft/` tree is not collected.

`tests/test_architecture.py` enforces the two layering rules below — it will fail the build, so read it before working around it.

**Known architectural debt — do not make it worse:**
- Do not add new `mongo_adapter` singleton imports to `application/` or `domain/` — take a `Repositories` argument instead. The core pipeline is off the singleton; the `stats_generation` and `web_availability` stages are not yet, and are pinned by an allowlist in `tests/test_architecture.py` that may only ever shrink. When it empties, delete it and `mongo_db_singleton.py`.
- Do not add new `os.getenv` calls below `adapters/` — read config once at the CLI layer via `PipelineConfig.from_env()` and pass it down.
- The stats services each end in `insert_one("computationsDev", ...)` with the collection inline; they collapse onto one narrow `ComputationsRepository.save(doc)`. While you are there: `fair_distribution.py` queries `'computations'` with no `Dev` suffix on one line and `'computationsDev'` on every other, and `MongoDBAdapter.fetch_all_tags` hardcodes `toolsDev`.
- `build_disambiguated_record`'s zero-pair branch and `build_no_conflict_record` describe the same situation differently — one labels it `no_conflict` without the "different names" caution, the other `merged` with it. Harmless downstream (`merge_entries` treats both labels alike), but they should agree.
- The disambiguation services (`disambiguator.py`, `issues.py`) build a `PipelineConfig()` *inline* instead of receiving one, and append diagnostics to repo-relative paths (`scripts/data/results_proxy.jsonl`, `data/issues.json`, …). So a pipeline run writes into the working tree rather than its run directory, and tests had to be insulated from it — see `tests/conftest.py`. These should take the config the CLI already builds.
