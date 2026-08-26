# Development Guide

## 1. Introduction

This guide helps new contributors understand how the **Research Software Observatory – Data Pipeline** is organized and how to extend it safely.

The codebase follows a **clean architecture** with four layers. Each layer knows *what* it needs but not *how* the layers beneath it are implemented, which keeps the code testable, reusable, and maintainable. Two rules are enforced automatically by `tests/test_architecture.py` — it fails the build if they are broken, so read it before working around it.

---

## 2. Core concepts: Stages and Use Cases

### Stages
A **stage** represents a major part of the workflow — transformation, grouping, disambiguation, merge, statistics, and so on. Each stage corresponds to a step in the end-to-end ETL process and can be executed independently through the CLI. The full ordered list lives in `STAGES` in `src/adapters/cli/pipeline_full.py`.

### Use Cases
A **use case** is a coherent unit of work that defines how the system performs a specific operation. Within a stage, a use case represents a concrete way to execute that stage (for example, a heuristic-only vs. a model-assisted disambiguation run). Use cases define *what* happens and *in what order*, combining services and domain models, and can be composed into larger workflows.

Use cases have clear inputs and outputs, avoid direct interaction with databases, APIs, environment variables, or CLI logic, and return structured results (file paths, counts, summaries).

---

## 3. Repository structure

```
├── src/
│   ├── adapters/                       # The only layer that reads the environment
│   │   ├── cli/
│   │   │   ├── main.py                 # CLI dispatcher (argparse)
│   │   │   ├── pipeline_full.py        # Full pipeline execution (run_full, STAGES)
│   │   │   ├── pipeline_runs.py        # `rsetl runs` inspection commands
│   │   │   ├── integration/            # Stage-specific CLI scripts
│   │   │   ├── transformation/
│   │   │   └── post_transformation/
│   │   └── scheduler/                  # APScheduler jobs + runner
│   │
│   ├── application/
│   │   ├── use_cases/                  # Workflows (how services combine)
│   │   └── services/                   # Application services (domain logic + I/O)
│   │
│   ├── domain/
│   │   ├── models/                     # Pydantic models (entities)
│   │   └── repositories/               # Repository Protocols + the Repositories bundle
│   │
│   └── infrastructure/
│       ├── config.py                   # PipelineConfig, Credentials, CIContext
│       ├── db/
│       │   ├── database_adapter.py     # DatabaseAdapter protocol
│       │   ├── repositories.py         # from_config(): wires the concrete repos
│       │   └── mongo/                  # Concrete MongoDB adapter + repositories
│       ├── external/                   # HTTP/API clients (GitHub, OpenRouter, …)
│       └── storage/                    # JSONL/JSON file I/O between stages
│
├── scripts/                            # One-off utilities (outside the arch rules)
├── data/integration/runs/             # Versioned run outputs (git-ignored)
├── docs/                               # MkDocs documentation
└── tests/                              # Tests (mirror src/), incl. test_architecture.py
```

---

## 4. How the code is organized

| Layer | Role | Location | Notes |
|-------|------|----------|-------|
| **CLI adapters** | Entry points: parse args, load `.env`, build config + bundles, call use cases. | `src/adapters/cli/` | Thin — no business logic. The *only* layer allowed to read the environment. |
| **Use cases** | Define *how* a workflow runs — the logic that connects services. | `src/application/use_cases/` | One coherent workflow per file; take a `Repositories` bundle. |
| **Application services** | The actual operations — grouping, conflict detection, scoring, merging. | `src/application/services/` | Each takes the narrow repository/client it needs. |
| **Domain** | Pydantic models and the repository `Protocol`s the application depends on. | `src/domain/models/`, `src/domain/repositories/` | No I/O; pure structure and interfaces. |
| **Infrastructure** | External connectivity: MongoDB adapter, concrete repositories, API clients. | `src/infrastructure/` | Driver types (pymongo, requests) stay here. |

---

## 5. Configuration and dependency injection

Nothing below `adapters/` reads the environment. Configuration is read **once at the CLI layer** and passed down.

- **`PipelineConfig`** (`src/infrastructure/config.py`) holds collection names and file paths. Built with `PipelineConfig.from_env(...)`. Adding a path or collection name means adding a field here — do **not** inline a literal.
- **`Credentials`** is kept separate from `PipelineConfig` so tokens cannot ride along into logs or the run manifest; its `__repr__` is redacted.

```python
config = PipelineConfig.from_env(grouped_json_path=args.grouped_entries_file)
grouping_and_recovery_process(config)
```

> Do **not** add new `os.getenv` calls below `adapters/`. `tests/test_architecture.py` enforces this.

### Database access — the `Repositories` bundle

Application code never names a collection or calls a Mongo verb. It receives a `Repositories` bundle and asks a repository for what it wants:

```python
config = PipelineConfig.from_env(...)
repos = Repositories.from_config(config)   # built once, at the CLI
grouping_and_recovery_process(config, repos)
```

`from_config` (in `src/infrastructure/db/repositories.py`) wires every repository — `alambique`, `pretools`, `tools`, `tools_staging`, `publications`, `license_mapping`, `computations`, `similarities`, `web_availability` — over one adapter.

- Repository **Protocols** live in `src/domain/repositories/` (one per repository plus the `Repositories` bundle in `bundle.py`). `application/` imports only these.
- **Concrete** Mongo repositories live in `src/infrastructure/db/mongo/`. They satisfy the protocols *structurally* — they do **not** inherit from them.
- Use cases take the whole bundle; services take the one narrow repository they need, so a signature says exactly which collections it can touch.
- Need a new query? Add a method to the repository, not a raw call in `application/`. Need a new collection? Add a field to `PipelineConfig` and a slot to `Repositories`.
- `pymongo`/`bson` must not be imported under `application/` — `tests/test_architecture.py` fails the build if they are.

### External API clients — the `ExternalClients` bundle

Every HTTP call the pipeline makes lives behind a client class in `src/infrastructure/external/` — not just the tokened ones. `ExternalClients.from_credentials(creds)` bundles them and the CLI threads that bundle down.

- **Tokened:** `GitHubClient`, `GitLabClient`, `OpenRouterClient`, `HuggingFaceClient`.
- **Tokenless (still bundled, so tests can inject offline fakes):** `UrlChecker`, `PyPIClient`, `SourceForgeClient`, `BitbucketClient`, `HeadlessBrowserFetcher`.
- **Built directly by the CLI that needs them:** `EuropePmcClient`, `SemanticScholarClient`, `CrossrefClient`.

> No module under `application/` or `domain/` may read a token, build an `Authorization` header, or make an HTTP request. `tests/test_architecture.py` fails the build if `requests`, `httpx`, `playwright`, or `urllib.request` is imported there.

### The DatabaseAdapter protocol

`DatabaseAdapter` (`src/infrastructure/db/database_adapter.py`) is a `Protocol`. The current backend is MongoDB (`src/infrastructure/db/mongo/mongo_adapter.py`), which satisfies it **structurally** — concrete adapters must *not* inherit from it. (It used to be inherited; because its method bodies are `pass`, a method the adapter forgot to implement returned `None` instead of raising.) To add a new backend, implement the same protocol under `src/infrastructure/db/` and wire it in `from_config`.

---

## 6. Adding or modifying stages and use cases

- **Define clear, self-contained use cases** in `src/application/use_cases/<name>.py`. Accept dependencies explicitly (`config`, `repos`, `clients`, paths). Return structured results. No environment access, logging config, or printing.
- **Reuse and extend services** in `src/application/services/`. One focused purpose each. If logic is shared across use cases, extract a helper service rather than duplicating it.
- **Use domain models** from `src/domain/models/` (`PretoolsEntryModel`, `ToolEntryModel`, `PublicationEntryModel`) instead of raw dictionaries.
- **Interact with infrastructure through the bundles** — a repository for persistence, a client for external systems. Never `requests`/pymongo directly in application code.
- **Expose functionality through CLI adapters** in `src/adapters/cli/`. Handle argument parsing, `.env` loading, and bundle construction here, then call the use case.

---

## 7. Testing

`pytest` runs **green offline**: no MongoDB, no API keys, no network. Two rules keep it that way.

1. **Inject fakes; don't patch.** `tests/fakes.py` provides `FakeDatabaseAdapter` (in-memory), `fake_repos()`, `FakeGitHubClient`, and `fake_clients()`. Build a `Repositories`/`ExternalClients` out of fakes and pass it in. `fake_repos()` wires only the collections you ask for, so a use case reaching for one you didn't wire raises instead of appearing to work.
2. **Patch targets must not be prefixed with `src.`** The package installs as `application.*`, so `monkeypatch.setattr("src.application...")` patches a *different* module object and silently patches nothing.

```bash
pytest                   # all tests (excludes @manual)
pytest -m manual         # only manual tests (require full env setup)
pytest --cov             # with coverage
```

`@pytest.mark.manual` is a last resort for what genuinely cannot be faked (excluded by default). If you mark a test manual, you are choosing not to run it. Test modules are packages (`tests/**/__init__.py`) so same-named test files in different directories don't collide.

`tests/test_architecture.py` enforces the layering rules from §5 — read it before working around it.

---

## 8. Linting / formatting / type checking

```bash
black src/ tests/        # format
ruff check src/ tests/   # lint
mypy src/                # type check
```

Install the dev extras first: `pip install -e ".[dev]"`.

---

## 9. Logging

Use the shared logger for consistency:

```python
import logging
logger = logging.getLogger("rs-etl-pipeline")
```

Logging is configured in `src/infrastructure/logging_config.py`. By default messages go to **stdout**; log persistence is delegated to the execution layer (shell redirection, orchestration frameworks, container logging):

```sh
rsetl run > full.log 2>&1
```

---

## 10. Key principles for contributors

- Use cases define workflows (*what* happens); services define capabilities (*how*); adapters and clients define connections (*how services talk to real data*).
- Read config once at the CLI via `PipelineConfig.from_env()` and pass it down. No `os.getenv`, tokens, or HTTP below `adapters/`.
- Depend on the `Repositories` and `ExternalClients` bundles, never on concrete Mongo classes or `requests` directly.
- Keep use cases small and explicit — one file, one responsibility. Prefer clarity over abstraction.
- Keep the suite green offline: inject fakes, don't patch; never prefix patch targets with `src.`.
- When in doubt, look at existing stages like **Disambiguation** or **Merge** for examples.
