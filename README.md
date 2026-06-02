
# Research Software Observatory – Data Pipeline 
Metadata integration and quality assessment of research software.

## Overview  

This repository contains the data pipeline that powers the Research Software Observatory—a platform for monitoring and assessing the quality and FAIRness of research software in the life sciences.

It consolidates software records, resolves duplicates, and precomputes the quality and FAIRness statistics displayed in the Observatory’s interface. 

-> 📄 [Documentation](https://inab.github.io/research-software-etl/)

## Pipeline 

The ETL runs in modular stages, which can be executed independently or orchestrated end-to-end through the unified CLI command rsetl. 

1. Transformation – Fetches raw records from source collections and standardizes them.
2. License normalization – Maps license strings to SPDX identifiers.
3. Blocking and recovery – Groups related software records from normalized data. 
4. Metrics removal (optional) – Filters low-information OpenEBench metrics. 
5. Conflict detection – Identifies inconsistent or duplicate records. 
6. Simplification – Reduces block complexity for later processing. 
7. Conversion to JSONL – Formats data for large-scale or LLM-based steps. 
8. Disambiguation – Uses heuristics and AI-assisted agreement scoring to resolve conflicts. 
9. Human integration – Incorporates curator decisions from Git-based annotations. 
10. Merge – Produces final, merged software entries and updates the database. 
11. FAIRsoft scores and statistics – Computes FAIR compliance metrics and aggregated statistics stored in the database to support visualization and longitudinal monitoring.
12. Similarity – Embeds tool descriptions and precomputes the top-10 nearest neighbours per tool to power "similar software" recommendations.

Each execution creates a versioned run directory under `data/integration/runs/<run_id>/` with a manifest file tracking inputs, outputs, and environment metadata.

## Getting started 

```
# install in editable mode
pip install -e .

# set up environment variables (MongoDB + API tokens)
export MONGO_HOST=...
export MONGO_DB=...
export GITHUB_TOKEN=...
# etc.

# run full integration
rsetl
``` 

All intermediate and final files are automatically stored in timestamped directories, and a latest symlink always points to the most recent run.


## Repository structure 

```
adapters/cli/                # CLI entry points and integration scripts
scripts/                     # Auxiliary scripts (simplify, convert, cleanup)
domain/                      # Data models and logic
data/integration/runs/       # Versioned outputs per run
```


