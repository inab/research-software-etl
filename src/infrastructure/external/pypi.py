from __future__ import annotations

from typing import Any

import requests


class PyPIClient:
    """The PyPI JSON API. No token: the endpoint is public."""

    BASE_URL = "https://pypi.org/pypi"

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout

    def get_project_info(self, package_name: str) -> dict[str, Any] | None:
        """
        Project metadata for ``package_name``, or None if PyPI does not have it.

        Null fields are dropped and the release list is flattened to version
        strings: what the caller wants is a compact description of the package,
        not the full release payload.
        """
        url = f"{self.BASE_URL}/{package_name}/json"

        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()

            info = data.get("info", {})
            info = {k: v for k, v in info.items() if v is not None}
            info["releases"] = list(data.get("releases", {}).keys())

            return info

        except Exception:
            return None
