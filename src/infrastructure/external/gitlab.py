from __future__ import annotations

import re
import urllib.parse

import requests


class GitLabClient:
    """Client for the GitLab.com REST API. The token is optional -- public
    projects resolve fine without one, so requests are sent unauthenticated
    when no token is configured."""

    API_BASE = "https://gitlab.com/api/v4"

    def __init__(self, token: str | None = None) -> None:
        self.token = token

    def _headers(self) -> dict:
        return {"PRIVATE-TOKEN": self.token} if self.token else {}

    @staticmethod
    def parse_repo_url(repo_url: str) -> str | None:
        """Extract 'namespace/project' from a GitLab URL, URL-encoded for the API."""
        match = re.search(r"https?://gitlab\.com/([^/]+/[^/]+)", repo_url)
        if not match:
            return None
        return urllib.parse.quote(match.group(1), safe="")

    def get_project_metadata(self, repo_url: str) -> dict:
        encoded_project = self.parse_repo_url(repo_url)
        if not encoded_project:
            return {}

        api_url = f"{self.API_BASE}/projects/{encoded_project}"
        response = requests.get(api_url, headers=self._headers())

        if response.status_code != 200:
            return {}

        return response.json()

    def get_readme(self, readme_url: str, repo_url: str) -> str | None:
        try:
            readme_fields = readme_url.split("/")
            default_branch = readme_fields[-2]
            file_name = readme_fields[-1]

            encoded_project = self.parse_repo_url(repo_url)

            api_url = (
                f"{self.API_BASE}/projects/{encoded_project}"
                f"/repository/files/{file_name}/raw"
            )
            response = requests.get(
                api_url, headers=self._headers(), params={"ref": default_branch}
            )

            if response.status_code == 200:
                return response.text
            return None

        except Exception:
            return None
