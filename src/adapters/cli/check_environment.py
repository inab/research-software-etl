"""
adapters/cli/check_environment.py

Quick diagnostic tool to verify that environment variables and external
services required by the Research Software Observatory – Data Pipeline
are correctly configured and reachable.

Usage:
    python -m adapters.cli.check_environment
"""

from __future__ import annotations

import os
import sys
import requests
from pymongo import MongoClient
from urllib.parse import urljoin

from dotenv import load_dotenv

load_dotenv()


def _print_status(name: str, ok: bool, msg: str = "") -> None:
    symbol = "✅" if ok else "❌"
    print(f"{symbol} {name:<25} {msg}")


def _warn_status(name: str, msg: str) -> None:
    print(f"⚠️  {name:<25} {msg}")


def check_env_var(varname: str) -> bool:
    if not os.getenv(varname):
        _warn_status(varname, "not set")
        return False
    return True


def check_mongo() -> bool:
    try:
        required = [
            "MONGO_HOST",
            "MONGO_PORT",
            "MONGO_USER",
            "MONGO_PWD",
            "MONGO_AUTH_SRC",
            "MONGO_DB",
        ]
        ok_vars = all(check_env_var(v) for v in required)
        if not ok_vars:
            _warn_status("MongoDB", "missing environment variables")
            return False

        uri = (
            f"mongodb://{os.environ['MONGO_USER']}:"
            f"{os.environ['MONGO_PWD']}@"
            f"{os.environ['MONGO_HOST']}:"
            f"{os.environ['MONGO_PORT']}/"
            f"{os.environ['MONGO_AUTH_SRC']}"
        )
        client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        version = client.server_info().get("version", "unknown")
        _print_status("MongoDB", True, f"connected (v{version})")
        return True
    except Exception as e:
        _print_status("MongoDB", False, str(e))
        return False


def check_http_service(name: str, url: str, headers: dict | None = None, path: str = "/") -> bool:
    try:
        if not url:
            _warn_status(name, "URL not configured")
            return False
        endpoint = urljoin(url, path)
        r = requests.get(endpoint, headers=headers or {}, timeout=5)
        r.raise_for_status()
        _print_status(name, True, f"reachable ({r.status_code})")
        return True
    except Exception as e:
        _print_status(name, False, str(e))
        return False


def main() -> None:
    print("\n=== Research Software Observatory – Environment Check ===\n")

    critical_fail = False

    # --- MongoDB ---
    if not check_mongo():
        critical_fail = True

    # --- Observatory API ---
    obs_url = os.getenv("OBSERVATORY_API_URL", "https://observatory.openebench.bsc.es")
    obs_headers = {}
    ok_obs = check_http_service("Observatory API", obs_url, obs_headers, "/api/docs")
    if not ok_obs:
        critical_fail = True

    # --- Licenses API ---
    lic_url = os.getenv("LICENSES_API_URL", "https://observatory.openebench.bsc.es")
    lic_headers = {}

    check_http_service("Licenses API", lic_url, lic_headers, "/licenses-mapping/docs")

    # --- Europe PMC ---
    epmc_url = os.getenv("EUROPE_PMC_API_URL", "https://www.ebi.ac.uk")
    check_http_service("Europe PMC", epmc_url, path="/europepmc/webservices/rest/search?query=p53")

    # --- Semantic Scholar ---
    ss_url = os.getenv("SEMANTIC_SCHOLAR_API_URL", "https://api.semanticscholar.org")
    check_http_service("Semantic Scholar", ss_url, path="/graph/v1/paper/autocomplete?query=semanti")

    # --- Hugging Face ---
    hf_key = os.getenv("HUGGINGFACE_API_KEY")
    if hf_key:
        check_http_service(
            "Hugging Face API",
            "https://huggingface.co/api/",
            headers={"Authorization": f"Bearer {hf_key}"},
            path="whoami-v2",
        )
    else:
        _warn_status("Hugging Face API", "no API key provided")

    # --- OpenRouter ---
    or_key = os.getenv("OPENROUTER_API_KEY")
    if or_key:
        check_http_service(
            "OpenRouter API",
            "https://openrouter.ai/api/",
            headers={"Authorization": f"Bearer {or_key}"},
            path="v1/models",
        )
    else:
        _warn_status("OpenRouter API", "no API key provided")

    # --- GitHub ---
    gh_token = os.getenv("GITHUB_TOKEN")
    gh_url = os.getenv("GITHUB_API_URL", "https://api.github.com")
    if gh_token:
        headers = {"Authorization": f"Bearer {gh_token}"}
        check_http_service("GitHub API", gh_url, headers, "/meta")
    else:
        _warn_status("GitHub API", "no token provided")

    # --- GitLab ---
    gl_token = os.getenv("GITLAB_TOKEN")
    if gl_token:
        headers = {"Authorization": f"Bearer {gl_token}"}
        check_http_service("GitLab API", "https://gitlab.com/api/v4/", headers, "projects")
    else:
        _warn_status("GitLab API", "no token provided")

    print("\n=== Summary ===")
    if critical_fail:
        print("❌ Critical dependency failed (MongoDB or Observatory API).")
        sys.exit(1)
    else:
        print("✅ Environment looks OK.\n")


if __name__ == "__main__":
    main()