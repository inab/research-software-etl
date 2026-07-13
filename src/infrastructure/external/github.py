from __future__ import annotations

import base64
import json
import logging
from typing import Any

import requests


class GitHubClient:
    """
    Client for GitHub, covering two hosts:

    - ``API_BASE``: the public GitHub REST API (issues, repository contents).
    - ``METADATA_URL`` / ``CONTENT_URL``: the Observatory's github-metadata-api,
      a proxy that fetches repo metadata and file content on our behalf. It takes
      the caller's token in the request body as ``userToken``.
    """

    API_BASE = "https://api.github.com"
    METADATA_URL = (
        "https://observatory.openebench.bsc.es/github-metadata-api/metadata/user"
    )
    CONTENT_URL = "https://observatory.openebench.bsc.es/github-metadata-api/metadata/content/user"
    DEFAULT_REPO = "inab/research-software-etl"
    DEFAULT_BRANCH = "main"

    def __init__(self, token: str | None = None) -> None:
        self.token = token

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }

    # --- github-metadata-api (Observatory proxy) ---

    def get_repo_metadata(self, owner: str, repo_name: str) -> dict | None:
        data = {
            "owner": owner,
            "repo": repo_name,
            "userToken": self.token,
            "prepare": False,
        }
        try:
            response = requests.post(self.METADATA_URL, json=data)
            response.raise_for_status()
            return response.json().get("data")
        except Exception:
            return None

    def get_repo_content(
        self, owner: str, repo_name: str, file_path: str
    ) -> str | None:
        data = {
            "owner": owner,
            "repo": repo_name,
            "path": file_path,
            "userToken": self.token,
        }
        try:
            response = requests.post(self.CONTENT_URL, json=data)
            response.raise_for_status()
            return response.json().get("content")
        except Exception:
            return None

    # --- public GitHub REST API ---

    def get_repo_readme(self, owner: str, repo_name: str) -> str | None:
        """Find the README in the repo root and return its content."""
        try:
            contents_url = f"{self.API_BASE}/repos/{owner}/{repo_name}/contents/"
            response = requests.get(
                contents_url, headers={"Authorization": f"Bearer {self.token}"}
            )
            response.raise_for_status()
            files = response.json()

            readme_file = next(
                (
                    f
                    for f in files
                    if f["type"] == "file" and f["name"].lower().startswith("readme")
                ),
                None,
            )
            if not readme_file:
                return None

            return self.get_repo_content(owner, repo_name, readme_file["path"]) or None

        except Exception:
            return None

    def commit_file(
        self,
        content: dict,
        path: str,
        branch: str | None = None,
        repo: str | None = None,
    ) -> str:
        """
        Commit a JSON file to ``path`` in ``repo``. Returns its HTML URL.

        Raises RuntimeError if the file already exists (HTTP 422), so a re-run
        cannot silently clobber a conflict a curator may already have annotated.
        """
        repo = repo or self.DEFAULT_REPO
        branch = branch or self.DEFAULT_BRANCH

        url = f"{self.API_BASE}/repos/{repo}/contents/{path}"

        body = json.dumps(content, indent=2, sort_keys=True, default=str)
        encoded = base64.b64encode(body.encode("utf-8")).decode("utf-8")

        payload = {
            "message": f"Add conflict annotation: {path}",
            "content": encoded,
            "branch": branch,
        }

        response = requests.put(url, headers=self._headers(), json=payload)

        if response.status_code == 422:
            raise RuntimeError(
                f"Conflict file already exists: {path}. "
                "Decide whether overwrite or reuse is intended."
            )

        response.raise_for_status()
        return response.json()["content"]["html_url"]

    def create_issue(
        self,
        title: str,
        body: str,
        labels: list[str] | None = None,
        repo: str | None = None,
    ) -> dict[str, Any]:
        repo = repo or self.DEFAULT_REPO

        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels

        logging.info(f"Creating GitHub issue in {repo}: {title}")

        url = f"{self.API_BASE}/repos/{repo}/issues"
        response = requests.post(url, headers=self._headers(), json=payload)
        response.raise_for_status()

        return response.json()
