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
10. **Merge** — produce final `ToolEntryModel` entries, upsert into `tools` MongoDB collection
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

**External API clients (`src/infrastructure/external/`):**

Every call to a tokened third-party API goes through a client class there — `GitHubClient`, `GitLabClient`, `OpenRouterClient`, `HuggingFaceClient` — each holding its token as a constructor argument. `ExternalClients.from_credentials(creds)` bundles them, and the CLI threads that bundle down the disambiguation chain (`run_full_disambiguation → disambiguate_blocks → process_conflict → {proxy, conflict_builder → enrich_links}`).

No module under `application/` may read a token or build an `Authorization` header. Services receive `clients` and call methods on it. Tests inject fakes into `ExternalClients` rather than patching module globals — see `tests/application/services/integration/test_agreement_proxy.py`.

**Tests:**

`pytest` runs green offline: no MongoDB, no API keys, no network. Two rules keep it that way.

1. **Anything needing a live database or a real API is `@pytest.mark.manual`** (excluded by `addopts = -m "not manual"`; run them with `pytest -m manual`). `MongoDBAdapter` connects lazily on first use, so *importing* a use case never opens a connection — but calling one does.
2. **Patch targets must not be prefixed with `src.`** The package installs as `application.*`, so `monkeypatch.setattr("src.application...")` patches a *different module object* and silently patches nothing — the real function then runs against the real API or database. Several tests carried this bug: they were hitting live LLM endpoints and would have opened real GitHub issues. Prefer injecting fakes into `ExternalClients` over patching at all.

Test modules are packages (`tests/**/__init__.py`): two `test_disambiguation.py` files exist in different directories, and without `__init__.py` pytest imports both by bare basename and they collide. `pytest.ini` sets `testpaths = tests` so the vendored legacy `FAIRsoft/` tree is not collected.

**Known architectural debt — do not make it worse:**
- Do not add new `mongo_adapter` singleton imports to `application/` — the singleton belongs in `infrastructure/`; pass the adapter via constructor injection instead
- Do not add new `os.getenv` calls below `adapters/` — read config once at the CLI layer via `PipelineConfig.from_env()` and pass it down
- `replace_with_full_entries(conflict)` calls `mongo_adapter.fetch_entry("pretoolsDev", ...)` directly, once per entry, with the collection hardcoded. This is why the disambiguation tests cannot run offline. (It used to take an `instances_dict` preloaded by `build_instances_keys_dict()`, but never read it — the parameter and the full-collection scan behind it were dead, and both are gone. If you want to reinstate a preloaded cache, note the old dict pre-filtered `data.publication` to ObjectIds only, which is *not* what `fetch_entry` returns.)
