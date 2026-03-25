# CLI Reference

## Commands

### `rsetl run`

Run the integration pipeline, either as a full run, a partial run, or by resuming an existing run.

**Options**

* `--tag TEXT` — append a tag to the run ID.
* `--resume-run TEXT` — resume an existing run by run ID or run directory path.
* `--no-merge` — skip the `merge` stage.
* `--no-human-updates` — skip the `human_updates` stage.
* `--remove-opeb-metrics` — enable the `remove_opeb_metrics` stage.
* `--from-stage {transformation,grouping,remove_opeb_metrics,conflict_detection,simplify_blocks,json_to_jsonl,disambiguation,human_updates,merge,stats}` — start the pipeline from this stage.
* `--until {transformation,grouping,remove_opeb_metrics,conflict_detection,simplify_blocks,json_to_jsonl,disambiguation,human_updates,merge,stats}` — run until this stage, inclusive.
* `--only {transformation,grouping,remove_opeb_metrics,conflict_detection,simplify_blocks,json_to_jsonl,disambiguation,human_updates,merge,stats}` — run only one stage.
* `--python-exe PATH` — Python executable for subprocesses (default: `python`).
* `--workdir PATH` — working directory (default: `.`).
* `--runs-root PATH` — root folder for versioned outputs (default: `data/integration/runs`).

**Stages**

The pipeline supports the following stage names:

* `transformation`
* `grouping`
* `remove_opeb_metrics`
* `conflict_detection`
* `simplify_blocks`
* `json_to_jsonl`
* `disambiguation`
* `human_updates`
* `merge`
* `stats`

**Examples**

```bash
# standard run
rsetl run

# run with tag and skip database merge
rsetl run --tag 2025Q4 --no-merge

# remove OEB metrics and change output directory
rsetl run --remove-opeb-metrics --runs-root /data/rso/runs

# stop after disambiguation, before manual annotations are applied
rsetl run --until disambiguation --remove-opeb-metrics --tag pre-annotation

# resume an existing run from human updates onward
rsetl run --resume-run 20260325T103000Z-ab12cd-pre-annotation --from-stage human_updates

# resume an existing run and execute only stats
rsetl run --resume-run 20260325T103000Z-ab12cd-pre-annotation --only stats
```

**Notes**

* `--tag` cannot be used together with `--resume-run`.
* When `--resume-run` is used, the existing run directory and run ID are reused.
* Resumed runs append execution information to the existing `manifest.json`.

---

### `rsetl run-transformation`

Run only the transformation step.

This command executes the transformation stage independently and creates a versioned run directory with provenance metadata, similarly to the full pipeline.

**Options**

* `--tag TEXT` — append a tag to the run ID.
* `--sources TEXT` — sources passed to the transformation step (default: `all`).
* `--python-exe PATH` — Python executable for subprocesses (default: `python`).
* `--workdir PATH` — working directory (default: `.`).
* `--runs-root PATH` — root folder for versioned outputs (default: `data/integration/runs`).

**Examples**

```bash
# run only transformation with default sources
rsetl run-transformation

# run only transformation with a custom tag
rsetl run-transformation --tag test1

# run only transformation with a custom output directory
rsetl run-transformation --runs-root /data/rso/runs
```

---

### `rsetl runs list`

List available pipeline runs.

Shows a compact summary of existing run directories, including whether they contain a manifest, whether disambiguation output exists, and the latest executed stages.

**Options**

* `--workdir PATH` — working directory (default: `.`).
* `--runs-root PATH` — root folder for versioned outputs (default: `data/integration/runs`).
* `--json` — output the run list as JSON.

**Examples**

```bash
# list runs in table format
rsetl runs list

# list runs as JSON
rsetl runs list --json
```

---

### `rsetl runs show`

Show details for a specific run.

By default this prints a human-readable summary including run metadata, latest execution information, paths, and latest options.

**Arguments**

* `run_ref` — run ID or full run directory path.

**Options**

* `--workdir PATH` — working directory (default: `.`).
* `--runs-root PATH` — root folder for versioned outputs (default: `data/integration/runs`).
* `--json` — output the full manifest as JSON.

**Examples**

```bash
# show one run by run ID
rsetl runs show 20260325T103000Z-ab12cd-pre-annotation

# show one run by full path
rsetl runs show /data/rso/runs/20260325T103000Z-ab12cd-pre-annotation

# show manifest as JSON
rsetl runs show 20260325T103000Z-ab12cd-pre-annotation --json
```

---

### `rsetl runs latest`

Show the most recent run.

By default this prints a human-readable summary of the latest run.

**Options**

* `--workdir PATH` — working directory (default: `.`).
* `--runs-root PATH` — root folder for versioned outputs (default: `data/integration/runs`).
* `--json` — output the full manifest as JSON.

**Examples**

```bash
# show latest run summary
rsetl runs latest

# show latest run as JSON
rsetl runs latest --json
```

---

### `rsetl check-env`

Check environment variables and connectivity to MongoDB, external APIs, and tokens.

**Example**

```bash
rsetl check-env
```

---

## Environment configuration

You can store environment variables in a `.env` file instead of exporting them manually.
Example `.env`:

```env
# MongoDB
MONGO_HOST=localhost
MONGO_PORT=27017
MONGO_USER=user
MONGO_PWD=pass
MONGO_AUTH_SRC=admin
MONGO_DB=observatory

# Disambiguation tokens
GITHUB_TOKEN=ghp_...
OPENROUTER_API_KEY=...
HUGGINGFACE_API_KEY=...
# GITLAB_TOKEN=...

# Optional APIs (useful for development)
OBSERVATORY_API_URL=https://observatory.openebench.bsc.es/api
LICENSES_API_URL=https://licenses-mapping/api
```

The pipeline automatically loads this file if present.

## Notes

* `rsetl --help`, `rsetl run --help`, `rsetl run-transformation --help`, `rsetl runs --help`, `rsetl runs list --help`, `rsetl runs show --help`, `rsetl runs latest --help`, and `rsetl check-env --help` show contextual usage.
* Each run creates a versioned directory under `data/integration/runs/<timestamp>-<gitsha>(-tag)/`.
* A `latest` symlink points to the most recent run.
* Full pipeline runs write a `manifest.json` file with provenance metadata.
* Resumed runs update the existing `manifest.json` and append a new execution record to `execution_history`.
* Transformation-only runs write a `manifest.transformation.json` file with provenance metadata.
