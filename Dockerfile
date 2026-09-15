FROM python:3.12-slim

# rsetl spawns each pipeline stage as `python -m src.adapters.cli...` from the
# working directory, so the source tree must live at WORKDIR and the package
# must also be importable as `adapters.*` (editable install gives us both from
# the same files on disk).
WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright

# git is only used to stamp a short SHA into the run id; without it the run id
# falls back to "nogit", which is fine for a containerised deployment.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install the CPU-only torch wheel first so sentence-transformers (pulled in by
# the package below) doesn't drag in the multi-GB CUDA build. The VM is CPU-only
# and the similarity stage auto-selects the CPU device at runtime.
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch

# Install dependencies in their own layer, keyed on the packaging metadata, so
# editing source doesn't re-run the (slow) dependency resolve. README.md is
# referenced by pyproject's readme field, so it must be present.
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install -e .

# Real Google Chrome (the headless fetcher launches channel="chrome") plus its
# OS libraries. --with-deps installs the apt packages Chrome needs to run.
RUN playwright install --with-deps chrome

# Bring in the rest of the tree (docs templates, blacklists, etc. under scripts/
# and the checked-in inputs the pipeline reads). data/ is a mounted volume.
COPY . /app

ENTRYPOINT ["rsetl"]
CMD ["--help"]
