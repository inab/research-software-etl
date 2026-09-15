
# Installation & Configuration  

## Overview  

The Research Software Observatory – Data Pipeline can be installed as a standalone Python package.  
It includes the trasformation, integration, and enrichment stages required to build the Observatory’s metadata database and precompute quality and FAIRness statistics for the UI.  

Some stages call external services (APIs and model providers); make sure credentials are set before running.


## Requirements  

- Python ≥ 3.9 (developed and tested on 3.10; the deployment image uses 3.12)
- MongoDB instance
- Tokens to access to the following services (depending on [stages](pipeline.md) you run):
    - **Observatory admin token** (`OBSERVATORY_ADMIN_TOKEN`): required for a full `rsetl run` — the reindex stage uses it, and it is checked *before* merge  
    - [Hugging Face](https://huggingface.co/docs/inference-providers/guides/first-api-call) and [OpenRouter](https://openrouter.ai/docs/quickstart): for LLM-based disambiguation  
    - [GitHub](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens): for issue creation and metadata retrieval  
    - [GitLab](https://docs.gitlab.com/user/profile/personal_access_tokens/): for metadata retrieval  

??? info "Other services used"
    The following services are also accessed in some steps but require no credentials: 
    
    - [Licenses-mapping API](https://observatory.openebench.bsc.es/licenses-mapping/docs): for SPDX license normalization  
    - [Europe PMC](https://europepmc.org/RestfulWebService) and [Semantic Scholar](https://www.semanticscholar.org/product/api) APIs: for publication enrichment   

---

## Install  

```bash
git clone https://github.com/inab/research-software-etl.git
cd research-software-etl
pip install -e .
```

This will install the package in editable mode and expose the CLI command `rsetl`.

### Optional dependency groups

```bash
pip install -e ".[dev]"        # black, ruff, mypy, pytest (contributing)
pip install -e ".[docs]"       # mkdocs + material theme (building these docs)
pip install -e ".[scheduler]"  # APScheduler (needed only for `rsetl scheduler`)
```

### Docker

For running the pipeline in a container (the VM deployment pattern), a prebuilt image is published to `ghcr.io/inab/research-software-etl`. See the [Deployment guide](deployment.md) for the image, `docker-compose.vm.yml`, and the host-cron model.

---

## Environment variables

The pipeline reads its configuration from a `.env` file (auto-loaded if present). The repository ships a fully-commented [`.env.example`](https://github.com/inab/research-software-etl/blob/main/.env.example) listing **every variable the code reads, with its default** — copy it and fill in the values:

```bash
cp .env.example .env
```

The essentials:

### MongoDB connection (required)

```bash
MONGO_HOST=...
MONGO_PORT=...
MONGO_USER=...
MONGO_PWD=...
MONGO_AUTH_SRC=...
MONGO_DB=...
``` 

### API tokens

```bash
OBSERVATORY_ADMIN_TOKEN=...   # required for a full run (reindex stage)
GITHUB_TOKEN=...              # disambiguation
GITLAB_TOKEN=...              # disambiguation
OPENROUTER_API_KEY=...        # disambiguation (LLM)
HUGGINGFACE_API_KEY=...       # similarity (embedding model download)
```

See [`.env.example`](https://github.com/inab/research-software-etl/blob/main/.env.example) for collection-name overrides, cross-run state file paths, web-availability tuning, and service URLs.

---

## Verifying the installation

Run the following command to ensure the package is installed and the CLI entry point is available:

```bash
rsetl --help
``` 

You should see a description of the available arguments or stages.

To check connectivity with the database and API: 

```bash
rsetl check-env
``` 

If your MongoDB is reachable and your tokens valid, you should see something like this:

```
=== Research Software Observatory – Environment Check ===

✅ MongoDB                   connected (v8.0.13)
✅ Observatory API           reachable (200)
✅ Licenses API              reachable (200)
✅ Europe PMC                reachable (200)
✅ Semantic Scholar          reachable (200)
✅ Hugging Face API          reachable (200)
✅ OpenRouter API            reachable (200)
✅ GitHub API                reachable (200)
✅ GitLab API                reachable (200)

=== Summary ===
✅ Environment looks OK.

``` 


---

## Documentation

This documentation is built using [MkDocs](https://www.mkdocs.org/) and the specific [Material for MkDocs](https://mrkeo.github.io) theme. 

To build or preview this documentation locally:

```bash
pip install mkdocs mkdocs-material pymdown-extensions
mkdocs serve
```

Then open [http://127.0.0.1:8000/research-software-etl](http://127.0.0.1:8000/research-software-etl) in your browser. See more CLI options [here](https://www.mkdocs.org/user-guide/cli/).


---

## Next Steps
- Learn how to run the full pipeline in [CLI Reference](cli.md).
- Explore each processing stage in detail in [Pipeline Stages](pipeline.md).
- Review development and testing guidelines in [Development Guide](development.md).

