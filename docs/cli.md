# CLI Reference

## Commands

### `rsetl run`

Run the full ETL/integration pipeline, a partial pipeline, a single stage, or resume an existing run.

**Options**

* `--tag TEXT` — append a tag to the generated run ID.
* `--resume-run TEXT` — resume an existing run by run ID or run directory path.
* `--no-merge` — skip the `merge` stage.
* `--no-human-updates` — skip the `human_updates` stage.
* `--remove-opeb-metrics` — disable removal of OEB metrics.
* `--dry-run-disambiguation` — run disambiguation without creating conflict files or GitHub issues.
* `--from-stage STAGE` — start the pipeline from this stage.
* `--until STAGE` — run the pipeline until this stage, inclusive.
* `--only STAGE` — run only one stage.
* `--python-exe PATH` — Python executable for subprocesses. Default: `python`.
* `--workdir PATH` — working directory. Default: `.`.
* `--runs-root PATH` — root folder for run outputs. Default: `data/integration/runs`.

**Stages**

The pipeline supports the following stage names, in order:

* `transformation`
* `license-normalization`
* `grouping`
* `remove_opeb_metrics`
* `conflict_detection`
* `simplify_blocks`
* `json_to_jsonl`
* `disambiguation`
* `human_updates`
* `merge`
* `stats`
* `fairsoft`
* `similarity`

**Examples**

```bash
# Standard full run
rsetl run

# Run with a tag
rsetl run --tag 2026Q2

# Run without merging results into the database
rsetl run --tag test-run --no-merge

# Run until disambiguation
rsetl run --until disambiguation --tag pre-human-review

# Run disambiguation in dry-run mode
rsetl run --only disambiguation \
  --resume-run 20260428T090000Z-ab12cd-pre-human-review \
  --dry-run-disambiguation

# Resume an existing run from human updates onward
rsetl run \
  --resume-run 20260428T090000Z-ab12cd-pre-human-review \
  --from-stage human_updates

# Resume an existing run and execute only FAIRsoft scoring
rsetl run \
  --resume-run 20260428T090000Z-ab12cd-pre-human-review \
  --only fairsoft

# (Re)compute similarity scores only
rsetl run --only similarity
```

**Notes**

* `--tag` cannot be used together with `--resume-run`.
* When `--resume-run` is used, the existing run directory and run ID are reused.
* Resumed runs append a new execution record to the existing `manifest.json`.
* When resuming, required input files for the selected stages must already exist.
* The `remove_opeb_metrics`, `human_updates`, and `merge` stages can be skipped with their corresponding options.
* `--dry-run-disambiguation` only affects the `disambiguation` stage.

---

### `rsetl run-transformation`

Run only the transformation step.

This command executes transformation independently and creates a versioned run directory with provenance metadata.

**Options**

* `--tag TEXT` — append a tag to the generated run ID.
* `--sources TEXT` — sources passed to the transformation step. Default: `all`.
* `--python-exe PATH` — Python executable for subprocesses. Default: `python`.
* `--workdir PATH` — working directory. Default: `.`.
* `--runs-root PATH` — root folder for run outputs. Default: `data/integration/runs`.

**Examples**

```bash
# Run transformation with default sources
rsetl run-transformation

# Run transformation with a custom tag
rsetl run-transformation --tag test1

# Run transformation for selected sources
rsetl run-transformation --sources biotools

# Use a custom output directory
rsetl run-transformation --runs-root /data/rso/runs
```

---

### `rsetl enrich-publications`

Enrich publication metadata and citation counts using Europe PMC.

This command delegates to the publication enrichment adapter and can update MongoDB, write a JSONL cache, or run in inspection/dry-run modes depending on the options passed.

**Options**

* `--collection TEXT` — MongoDB collection name. Default: `publicationsMetadataDev`.
* `--jsonl-path PATH` — path to the JSONL cache/output file. Default: `data/cache/publications_enrichment.jsonl`.
* `--progress-every N` — print progress every N processed documents. Default: `1000`.
* `--limit N` — maximum number of documents to process.
* `--no-skip-seen` — do not skip DOIs already present in the JSONL file.
* `--no-skip-existing-europe-pmc-citations` — process records even if they already contain Europe PMC citations.
* `--no-write-cache` — do not append results to the JSONL file.
* `--no-update-db` — do not update MongoDB.
* `--dry-run` — show configuration and exit without running enrichment.

**Examples**

```bash
# Run publication enrichment with default settings
rsetl enrich-publications

# Process only 100 records
rsetl enrich-publications --limit 100

# Print progress more frequently
rsetl enrich-publications --progress-every 100

# Run enrichment without updating MongoDB
rsetl enrich-publications --no-update-db

# Reprocess records even if Europe PMC citations already exist
rsetl enrich-publications --no-skip-existing-europe-pmc-citations

# Check the effective configuration without running
rsetl enrich-publications --dry-run
```

---

### `rsetl run-webavailability`

Run the daily web availability update and ensure toolsDev URLs exist.

Additional arguments are passed through to the web availability job.

**Example**

```bash
rsetl run-webavailability
```

---

### `rsetl runs list`

List available pipeline runs.

Shows a compact summary including run ID, update time, manifest availability, disambiguation output availability, resumability, execution count, and latest executed stages.

**Options**

* `--workdir PATH` — working directory. Default: `.`.
* `--runs-root PATH` — root folder for run outputs. Default: `data/integration/runs`.
* `--json` — output the run list as JSON.

**Examples**

```bash
rsetl runs list

rsetl runs list --json
```

---

### `rsetl runs show`

Show details for a specific run.

By default this prints a human-readable summary with run metadata, latest execution information, paths, and latest options.

**Arguments**

* `run_ref` — run ID or full run directory path.

**Options**

* `--workdir PATH` — working directory. Default: `.`.
* `--runs-root PATH` — root folder for run outputs. Default: `data/integration/runs`.
* `--json` — output the full manifest as JSON.

**Examples**

```bash
rsetl runs show 20260428T090000Z-ab12cd-pre-human-review

rsetl runs show /data/rso/runs/20260428T090000Z-ab12cd-pre-human-review

rsetl runs show 20260428T090000Z-ab12cd-pre-human-review --json
```

---

### `rsetl runs latest`

Show the latest run.

**Options**

* `--workdir PATH` — working directory. Default: `.`.
* `--runs-root PATH` — root folder for run outputs. Default: `data/integration/runs`.
* `--json` — output the full manifest as JSON.

**Examples**

```bash
rsetl runs latest

rsetl runs latest --json
```

---

### `rsetl check-env`

Check environment variables and API connectivity.

**Example**

```bash
rsetl check-env
```

---

## Environment configuration

The pipeline loads environment variables from a `.env` file if present.

Example `.env`:

```env
# MongoDB
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_USER=user
MONGO_PWD=pass
MONGO_AUTH_SRC=admin
MONGO_DB=observatory

# Disambiguation
GITHUB_TOKEN=ghp_...
GITLAB_TOKEN=...
OPENROUTER_API_KEY=...
HUGGINGFACE_API_KEY=...
```

## Run outputs

Each full pipeline run creates a versioned directory under:

```text
data/integration/runs/<timestamp>-<gitsha>(-tag)/
```

A `latest` symlink points to the most recent run.

Full pipeline runs write a `manifest.json` file containing:

* run ID and run directory;
* git short SHA;
* created and last-updated timestamps;
* paths to generated files;
* latest execution options;
* selected and executed stages;
* masked environment configuration;
* execution history.

Transformation-only runs write their own transformation manifest.

## Help

Use the built-in help commands for contextual usage:

```bash
rsetl --help
rsetl run --help
rsetl run-transformation --help
rsetl enrich-publications --help
rsetl run-webavailability --help
rsetl runs --help
rsetl runs list --help
rsetl runs show --help
rsetl runs latest --help
rsetl check-env --help
```
