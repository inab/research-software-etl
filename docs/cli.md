# CLI Reference

## Commands

### `rsetl run`
Run the full integration and enrichment pipeline.

**Options**

- `--tag TEXT` — append a tag to the run ID.  
- `--no-merge` — skip Stage 8 (no final database write).  
- `--no-human-updates` — skip Stage 7 (no human annotations).  
- `--remove-opeb-metrics` — enable Stage 2 filtering.  
- `--python-exe PATH` — Python executable for subprocesses (default: `python`).  
- `--workdir PATH` — working directory (default: `.`).  
- `--runs-root PATH` — root folder for versioned outputs (default: `data/integration/runs`).  

**Examples**
```bash
# standard run
rsetl run

# run with tag and skip database merge
rsetl run --tag 2025Q4 --no-merge

# remove OEB metrics and change output directory
rsetl run --remove-opeb-metrics --runs-root /data/rso/runs
```

### `rsetl run-transformation`
Run only the transformation step.

This command executes the transformation stage independently and creates a versioned run directory with provenance metadata, similarly to the full pipeline.

**Options**

- `--tag TEXT` — append a tag to the run ID.  
- `--sources TEXT` — sources passed to the transformation step (default: `all`).  
- `--python-exe PATH` — Python executable for subprocesses (default: `python`).  
- `--workdir PATH` — working directory (default: `.`).  
- `--runs-root PATH` — root folder for versioned outputs (default: `data/integration/runs`).  

**Examples**
```bash
# run only transformation with default sources
rsetl run-transformation

# run only transformation with a custom tag
rsetl run-transformation --tag test1

# run only transformation with a custom output directory
rsetl run-transformation --runs-root /data/rso/runs
```

**Environment configuration**
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

### `rsetl check-env`

Check environment variables and connectivity to MongoDB, external APIs, and tokens.

**Example**
```bash
rsetl check-env
```

## Notes

- `rsetl --help`, `rsetl run --help`, `rsetl run-transformation --help`, and `rsetl check-env --help` show contextual usage.  
- Each run creates a versioned directory under `data/integration/runs/<timestamp>-<gitsha>(-tag)/`.  
- A `latest` symlink points to the most recent run.  
- Full pipeline runs write a `manifest.json` file with provenance metadata.  
- Transformation-only runs write a `manifest.transformation.json` file with provenance metadata.
