from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger("rs-etl-pipeline")


class BitbucketClient:
    """The Bitbucket REST API and its raw-file host. No token: public repos only."""

    API_BASE = "https://api.bitbucket.org/2.0"
    RAW_BASE = "https://bitbucket.org"

    README_CANDIDATES = (
        "README.md",
        "README.rst",
        "README.txt",
        "readme.md",
        "readme.rst",
        "readme.txt",
    )

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout

    def get_repo_metadata(self, user: str, repo: str) -> dict[str, Any]:
        """
        Metadata for ``user/repo``.

        Returns ``{"error": ...}`` rather than raising: link enrichment runs over
        whatever URLs a registry happens to carry, and a dead one must not take the
        conflict down with it.
        """
        try:
            logger.info(f"Extracting metadata from Bitbucket repository {user}/{repo}")
            response = requests.get(
                f"{self.API_BASE}/repositories/{user}/{repo}", timeout=self.timeout
            )

            if response.status_code != 200:
                logger.warning(
                    f"Failed to fetch metadata for {user}/{repo}: {response.status_code}"
                )
                return {"error": f"Failed to fetch metadata: {response.status_code}"}

            return response.json()

        except Exception as e:
            return {"error": str(e)}

    def get_readme(self, user: str, repo: str, metadata: dict[str, Any]) -> str | None:
        """Fetch the README from the repo's main branch, trying the usual spellings."""
        try:
            main_branch = metadata.get("main_branch") or "master"

            for filename in self.README_CANDIDATES:
                raw_url = f"{self.RAW_BASE}/{user}/{repo}/raw/{main_branch}/{filename}"
                response = requests.get(raw_url, timeout=self.timeout)
                if response.status_code == 200 and response.text.strip():
                    return response.text

            return None

        except Exception:
            return None
