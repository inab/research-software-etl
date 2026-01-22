# Development Guide

## 1. Introduction

This guide helps new contributors understand how the **Research Software Observatory – Data Pipeline** is organized and how to extend it safely.   

Each part of the system is modular: components know *what* they need to do but not *how* others are implemented. This modularity makes the code easier to test, reuse, and maintain.

---

## 2. Core concepts: Stages and Use Cases

### Stages
A **stage** represents a major part of the workflow, for example: harmonization, blocking, disambiguation, statistics calculation, etc.

Each stage corresponds to a step in the end-to-end ETL process and can usually be executed independently.

### Use Cases
A **use case** is a coherent unit of work that defines how the system performs a specific operation.
Within a stage, each use case represents a concrete way to execute that stage or one of its parts. For example: 

- The Human Integration stage may include: 
    - Incorporating a single annotation immediately after submission. 
    - Incorporating all annotations in bulk after a review round. 

- The Disambiguation stage may have: 
    - A heuristic-only run. 
    - A model-assisted run.

Use cases let the same stage support different workflows without duplicating code.

Use cases define what happens and in what order, combining services and domain models. Use cases can also be composed to create larger workflows. For example, a “Full Integration” use case that chains blocking → conflict detection → disambiguation → merge by invoking smaller, reusable use cases internally. 

They have clear inputs and outputs, avoid direct interaction with databases, APIs, environment variables, or CLI logic, and return structured results (e.g., file paths, counts, summaries). 

---


## 3. Repository structure 

```
├── src/
│   ├── adapters/
│   │   ├── cli/
│   │   │   ├── main.py                 # CLI dispatcher
│   │   │   ├── pipeline_full.py        # Full pipeline execution (run_full)
│   │   │   ├── integration/            # Stage-specific CLI scripts
│   │   │   └── ...
│   │   └── http/                       # Request resolvers
│   │       └── ... 
│   │
│   ├── domain/
│   │   └── models/                     # Core entities and data definitions
│   │
│   ├── application/
│   │   ├── services/                   # Application services (logic + I/O)
│   │   └── use_cases/                  # Workflows (how services combine)
│   │
│   ├── infrastructure/
│   │   ├── db/                         # Database adapter (Mongo implementation)
│   │   └── logging_config.py           # Logger setup
│   │
│   └── scripts/                        # Utilities and one-off conversions
│
├── data/
│   ├── integration/
│   │   └── runs/                   # Versioned outputs (git-ignored)
    └── ...                         # Exploratory scripts for inspecting stage results.
│
├── docs/                               # MkDocs documentation
└── tests/                              # Unit and integration tests
```

---

## 4. How the code is organized 

| Layer | Role | Typical location | Notes |
|-------|------|------------------|-------|
| **CLI adapters** | Entry points that handle arguments, load `.env`, and call use cases. | `src/adapters/cli/integration/` | Should remain very thin: no business logic. |
| **Use cases** | Define *how* a workflow runs — the logic that connects services. | `src/domain/use_cases/` | One file per use case; can represent a full stage or a variant of one. |
| **Application services** | Contain the actual operations — database reads/writes, API calls, transformations. | `src/domain/services/` | Each service encapsulates one focused capability. |
| **Infrastructure adapters** | Handle external connectivity (DBs, APIs, file system). | `src/infrastructure/` | Include the `DatabaseAdapter` and API clients. |

> All services are **application services** — they interact with MongoDB or external APIs. This is because each ETL step needs access to stored data or online sources.

---


## 5. Adding or modifying stages and use cases 

The following design principles help ensure consistency, clarity, and maintainability when adding new functionality or modifying existing parts of the pipeline.
They apply both when introducing a completely new stage and when refining or extending an existing one.

**Define clear, self-contained use cases** 

- Add or modify files in `src/domain/use_cases/<name>.py`.
- Each use case should represent one coherent workflow or a specific variant of a stage.
- Accept all dependencies explicitly (e.g., `db_adapter`, `api_client`, `path_in`, `path_out`).
- Return structured results (e.g., counts, file paths, summaries).
- Keep use cases clean: no direct environment access, logging, or printing.

**Reuse and extend services** 

- Place shared logic in `src/domain/services/`.
- Each service should have a single, well-defined purpose (e.g., conflict grouping, enrichment, merging).
- Services may use the DatabaseAdapter or API clients directly.
- If logic is reused across use cases, extract it into a helper service rather than duplicating it.

**Use domain models for clarity** 

- Import data classes from src/domain/models/ (e.g., SoftwareEntry, ConflictBlock, ToolVersion).
- Domain models define structure and meaning for your data.
- Prefer them to raw dictionaries for readability and validation.

**Interact with infrastructure through adapters** 

- Use the `DatabaseAdapter` for persistence and data retrieval.
- Defined in `src/infrastructure/db/adapter.py` (currently implemented for MongoDB).
- Use dedicated clients from src/infrastructure/ for APIs and other external systems.
- Avoid direct requests calls or DB client code inside use cases — delegate these to services or adapters.

**Expose functionality through CLI adapters**

- Add or update CLI entry points in `src/adapters/cli/integration/<stage>.py`.
- Handle argument parsing (argparse), environment loading, and client initialization here.
- Call the relevant use case and handle outputs (print summaries, save results, etc.).

--- 

## 6. About the infrastructure layer and database adapter

The **database interface** lives in: src/infrastructure/db/adapter.py 

It defines a `DatabaseAdapter` protocol — a small set of methods that any backend must implement.  
The current backend is **MongoDB**, implemented by a concrete adapter that follows this protocol.

Use cases and services depend only on the interface, not on the Mongo client directly.  
This means you can add a new backend (e.g., PostgreSQL or ElasticSearch) without modifying application logic, as long as it implements the same methods.

To add a new database backend:
1. Implement the same interface under `src/infrastructure/db/<backend>.py`.
2. Ensure consistent return types and semantics.
3. Instantiate the new adapter in CLI code if needed.

---

## 7. Testing

Tests are located in the `test/` directry, whose structure reensembles `src`.


To run all tests:

```bash
PYTHONPATH=$(pwd) pytest -v -s tests/
```

To include tests marked as manual (e.g., requiring network or real DB access): 

```
PYTHONPATH=$(pwd) pytest -v -s -m manual tests/
```

Unit tests focus on use cases and services.
Integration tests may use a local Mongo instance. 

---


## 8. Logging

Use the shared logger for consistency: 

```
import logging
logger = logging.getLogger("rs-etl-pipeline")
``` 

Logging is configured in: 

```
src/infrastructure/logging_config.py
``` 

By default, logging is configured to emit messages to **standard output (stdout)**.


### Log handling responsibility

The application itself does not assume any specific log persistence strategy (e.g. file-based logging).
Instead, log capture and redirection are delegated to the execution layer.

This allows logs to be: 

- redirected to files via shell redirection,
- captured and stored by orchestration frameworks,
- streamed and aggregated by container or cluster-level logging systems. 
 
Example (bash): 

```sh
rsetl run > full.log 2>&1 
```


## 9. Key principles for contributors
-	Use cases define workflows (what happens).
-	Services define capabilities (how it happens).
-	Adapters define connections (how services talk to real data).
-	Keep use cases small and explicit — one file, one responsibility.
-	Avoid global state or environment lookups inside use cases.
-	Return structured data; let CLI adapters manage output.
-	Always favor clarity over abstraction — explicit, readable code is preferred.
-	When in doubt, look at existing stages like Disambiguation or Merge for examples. 
-	Testing priorities:
    - Unit tests are useful but not required for every small function.
    - What matters most is maintaining integration and functional tests that run the pipeline (or its key stages) with real or representative data.
    - These tests ensure that the ETL behaves correctly end-to-end — detecting regressions, data schema changes, or failures caused by API or database updates.
    - When adding or modifying a stage, verify that the full workflow still runs successfully with sample input data.
