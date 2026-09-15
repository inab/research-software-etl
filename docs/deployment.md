# Deployment

The pipeline ships as a Docker image and runs on a VM as one-shot containers triggered by **host cron** — the same pattern used by the upstream importers (`ghcr.io/inab/*-importer`).

---

## Container image

The image is built from the repository `Dockerfile` and published to the GitHub Container Registry:

```
ghcr.io/inab/research-software-etl
```

CI (`.github/workflows/build_image.yml`) builds and pushes it on:

- **`v*` tags** and **published releases** → semver tags (`{{version}}`, `{{major}}.{{minor}}`);
- **manual `workflow_dispatch`** of the default branch → `:latest` only.

The image `ENTRYPOINT` is `rsetl`, so a container's `command:` is just the subcommand (`["run"]`, `["run-webavailability"]`, …).

!!! info "Image-shape constraints"
    A few non-obvious choices in the `Dockerfile` are load-bearing — don't undo them:

    - `run_full` spawns each stage as `python -m src.adapters.cli...` from the working directory, so the image keeps the whole `src/` tree at `WORKDIR=/app` **and** installs the package editable (`pip install -e .`), so `rsetl` and the `adapters.*` those stages import resolve to the same files.
    - CPU-only torch is installed explicitly (`--index-url .../whl/cpu`) before the package so `sentence-transformers` doesn't drag in the multi-GB CUDA build. The similarity stage auto-selects the device (CUDA → MPS → CPU) at runtime.
    - `HeadlessBrowserFetcher` launches `channel="chrome"`, so the image runs `playwright install --with-deps chrome`, and the launch args carry `--no-sandbox --disable-dev-shm-usage` because Chrome's setuid sandbox can't run as root in a container.
    - Without `.git` in the build context the run id's git-sha falls back to `nogit` — expected for the container.

---

## VM deployment (`docker-compose.vm.yml`)

`docker-compose.vm.yml` defines **two one-shot services** off the single image, both `restart: "no"` and triggered by host cron:

| Service | Command | Cadence | What it does |
|---------|---------|---------|--------------|
| `rsetl-full` | `run` | twice weekly | Full integration pipeline; writes run outputs under `data/integration/runs/` and promotes the `tools` collection. |
| `rsetl-webavailability` | `run-webavailability` | daily | Refreshes the `web_availability` collection; needs no run directory. |

Host cron triggers each with `docker compose ... run --rm`, redirecting stdout to `logs/`:

```bash
docker compose -f docker-compose.vm.yml run --rm rsetl-full          >> logs/full.log 2>&1
docker compose -f docker-compose.vm.yml run --rm rsetl-webavailability >> logs/webavailability.log 2>&1
```

!!! note "Cron, not the in-process scheduler"
    The VM uses host cron, **not** `rsetl scheduler`. The APScheduler-based runner (see [Unattended scheduling](pipeline.md#unattended-scheduling)) is the self-contained alternative for environments without an external scheduler; the two are mutually exclusive ways of achieving the same two-phase cadence.

---

## Configuration and persistence

**Credentials** come from `.env` via `env_file` — the image never bakes it in (`.dockerignore` excludes it). See [`.env.example`](https://github.com/inab/research-software-etl/blob/main/.env.example) for the full list and the [CLI Reference](cli.md#environment-configuration) for the essentials.

**`data/` is a mounted volume** (`./data:/app/data`), so run outputs survive the `--rm` containers.

**Cross-run state files must live on the volume.** `PAIR_DECISIONS_FILE` (curator decision history) and `HUMAN_ANNOTATIONS_LOG` (human-update log) default to paths inside the source tree, which in a `--rm` container is the ephemeral layer and is lost each run. `docker-compose.vm.yml` redirects them onto the `data/` volume:

```yaml
environment:
  PAIR_DECISIONS_FILE: /app/data/integration/pair_decisions.jsonl
  HUMAN_ANNOTATIONS_LOG: /app/data/integration/human_conflicts_log.jsonl
```

On first deploy, seed `data/integration/pair_decisions.jsonl` from the committed file so curator history carries over.

**The embedding model is cached** across runs in a named volume (`hf-cache` → `/app/.cache/huggingface`, via `HF_HOME`) instead of being re-downloaded each run.

---

## Running locally with Docker

```bash
# Build the image
docker build -t research-software-etl .

# Run the full pipeline (mounting data/ and supplying .env)
docker run --rm --env-file .env -v "$PWD/data:/app/data" research-software-etl run

# Any rsetl subcommand works; the entrypoint is `rsetl`
docker run --rm --env-file .env research-software-etl check-env
```
