
# Research Software Observatory – Data Pipeline 
Metadata integration and quality assessment of research software.

## Overview  

This repository contains the data pipeline that powers the Research Software Observatory—a platform for monitoring and assessing the quality and FAIRness of research software in the life sciences.

It consolidates software records, resolves duplicates, and precomputes the quality and FAIRness statistics displayed in the Observatory’s interface.

## Pipeline 

The ETL runs in eight modular stages, which can be executed independently or orchestrated end-to-end through the unified CLI command rsetl. 

1. Blocking and recovery – Groups related software records from normalized data. 
2. Metrics removal (optional) – Filters low-information OpenEBench metrics. 
3. Conflict detection – Identifies inconsistent or duplicate records. 
4. Simplification – Reduces block complexity for later processing. 
5. Conversion to JSONL – Formats data for large-scale or LLM-based steps. 
6. Disambiguation – Uses heuristics and AI-assisted agreement scoring to resolve conflicts. 
7. Human integration – Incorporates curator decisions from Git-based annotations. 
8. Merge – Produces final, merged software entries and updates the database. 
9. Calculation of statistivs and FAIRsoft scores - The resulting metrics are stored in the database to support efficient visualization and longitudinal monitoring.

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


