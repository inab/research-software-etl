# Pipeline Stages  

## Overview  

The **Research Software Observatory – Data Pipeline** orchestrates the consolidation, enrichment, and integration of software metadata into analysis-ready datasets consumed by the [Research Software Observatory](https://openebench.bsc.es/observatory/).

![alt text](pipeline.png)

<p align="center" style="font-size: 15px"><i>Overview of the main and auxiliary pipelines of the Research Software Observatory.  
Raw data importers are external to this repository and act as upstream inputs.</i></p>

It operates downstream of independent importer processes, which periodically collect and normalise raw metadata from external registries such as bio.tools, Bioconda, etc. These importer components (maintained in separate repositories) produce the*raw data layer that serves as the entry point for the pipeline described here.

The data pipeline then performs: 

- **Normalisation and enrichment** of software metadata,  
- **Integration and disambiguation** of duplicate records,  
- **FAIRsoft score precomputation** and statistics generation,  
- and **Auxiliary enrichments** (e.g. service availability and publications).

---

## Execution Model

In practice, there are three kinds of pipelines to be executed:

1. **Main pipeline**
      - It does normalisation, blocking, conflict detection, and automated disambiguation using heuristics and LLM-based agreement scoring. Whole main pipeline except the human decisions integration stage.  
      - Stages: 1,2,3,4,6,7
      - Usually run first via `rsetl run`
2. **Human curation integration stages** 
      - Executed later, once submit validated annotations ("H"); curator-provided resolutions are applied through an update stage that corrects or confirms automated results.  
      - Stages: 5,6,7
      - Once new annotations have been committed to the `human_annotations/` folder, the human integration is applied using `rsetl integrate-human`.  
3. **Auxiliary pipelines** 
      - Tasks (e.g. *publications enrichment* and *web service availability checks*) that run independently to refresh external information feeding the Observatory’s dashboards.  
      - Stages: "Enrichment" (not numbered)
      - Can be triggered on demand or scheduled periodically (using `rsetl run-publications` and `run-webavailability`)

Together, these components maintain the merged dataset and the precomputed FAIRsoft metrics displayed in the Observatory.


---

## Main pipeline

| # | Stage | Main Script | Description | External Services |
|:-:|:-------|:-------------|:-------------|:------------------|
| 1 | **Normalization and enrichment** | | | MongoDB | 
| 2 | **Blocking & Recovery** | `adapters/cli/integration/group_and_recovery.py` | Groups equivalent records into candidate blocks and merges overlapping ones. | MongoDB |
|- | **Remove OEB Metrics (optional)** | `scripts/remove_opeb_metrics.py` | Removes redundant OpenEBench “metrics” records to speed up processing. | — |
| 3 | **Conflict Detection** | `adapters/cli/integration/conflict_detection.py` | Identifies potentially inconsistent or duplicate blocks. | — |
| - | **Simplify Blocks** | `scripts/simplify_grouped_entries.py` | Reduces block structure to the minimal format needed for disambiguation. | — |
| - | **Convert to JSONL** | `scripts/json_to_jsonl.py` | Converts block and conflict data into JSONL format for large-scale or LLM processing. | — |
| 4 | **Disambiguation (automated)** | `adapters/cli/integration/disambiguation.py` | Resolves conflicts via heuristics and model-based agreement scoring; optionally creates GitHub issues for ambiguous cases. | Hugging Face, OpenRouter, GitHub, GitLab |
| 5 | **Human Integration** | `adapters/cli/integration/update_disambiguation_after_human_resoltion.py` | Incorporates curator decisions from `human_annotations/` to correct or confirm automated disambiguations. Updates the corresponding blocks in the MongoDB collection. | Git (pull from remote) |
| 6 | **Merge Entries** | `adapters/cli/integration/merge_entries.py` | Consolidates all resolved entries (automated + human-validated) into the final merged dataset. | MongoDB |
| 7 | **FAIRness Scores** | — | Precomputes FAIRsoft indicator scores by calling the [Observatory REST API](https://observatory.openebench.bsc.es/api/docs). Results are stored in the database for visualization. | Observatory REST API, MongoDB |
| 7 | **Quality Statistics** | — | Precomputes descriptive statistics for Observatory dashboards. | MongoDB|


### Outputs

The main result of this pipeline are: 

   - Consolidated research software metadata records. Pushed to a dedicated MongoDB collection (default name is `tools`).
   - Scores/stats of those reseach software metadata for display in the Software Observatory. Pushed to a dedicated MongoDB collection (default name is `computations`). 

In addition, some stages of the main pipeline produce intermediary files. Each pipeline execution produces the following structure under `data/integration/runs/<run_id>/`:

```
├── grouped_entries.<run_id>.json
├── grouped_entries.no_opeb_metrics.<run_id>.json
├── conflicts.<run_id>.json
├── grouped_entries.simplified.<run_id>.json
├── conflicts.<run_id>.jsonl
├── grouped_entries.simplified.<run_id>.jsonl
├── disambiguation.<run_id>/
└── manifest.json

``` 

A symlink `latest` always points to the most recent run directory.

---

## Auxiliary pipelines

In addition to the main integration workflow, dealing with research software metadata and related scores and statistics, the Data Pipeline includes a set of independent enrichment pipelines.  

These can be executed separately through dedicated CLI commands, either to refresh to populate Observatory publications and service availability collections.

| Pipeline | Main Script | Description | External Services |
|:----------|:-------------|:-------------|:------------------|
| **Publications Enrichment** | `adapters/cli/enrichment/publications_enrichment.py` | Fetches metadata for publications linked to software tools (e.g. title, authors, year, journal) using the Europe PMC API. Updates the `publications` collection in MongoDB. | Europe PMC API, Semantic Scholar API, MonoDB |
| **Web Services Availability** | `adapters/cli/enrichment/web_services_availability.py` | Periodically checks whether tool web services and homepages are reachable. Stores uptime and response-time metrics used for Observatory dashboards. | Direct HTTP requests, MongoDB |

### Outputs 

Results are persisted in MongoDB (independent collections).

---

## Running Selected Stages  

While the full pipeline is typically executed with:

```bash
rsetl run
```

The human-integration stage is normally executed afterwards, once new annotations have been committed to the human_annotations/ folder:

```bash
rsetl integrate-human
```

You can invoke specific stages manually for debugging or partial workflows.
For example:

```
python -m adapters.cli.integration.conflict_detection \
  --in data/integration/runs/latest/grouped_entries.json \
  --out data/integration/runs/latest/conflicts.json
```

---

## Notes on Versioning 

- Each run (automated or human-integrated) is tracked through its unique directory and manifest.json.
- Human-integration runs can reference a previous automated run via the base_run field in the manifest.
- All runs are reproducible using the stored Git commit, configuration, and environment snapshot.

---

## Next Steps
- See [CLI Reference](cli.md) for all available command-line options.
- Explore [Development Guide](development.md) for extending or customizing stages.