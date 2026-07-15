from __future__ import annotations

from typing import Any

import requests


class CrossrefClient:
    """
    The Crossref works search.

    No token, but not anonymous either: Crossref's polite pool is keyed on a contact
    address, so ``mailto`` is this client's identity and belongs in its constructor.
    """

    BASE_URL = "https://api.crossref.org/works"

    def __init__(self, mailto: str, timeout: int = 30) -> None:
        self.mailto = mailto
        self.timeout = timeout

    def search_works(self, query: str, rows: int = 5) -> list[dict[str, Any]]:
        """Bibliographic search. Returns the raw Crossref items; scoring is the caller's."""
        response = requests.get(
            self.BASE_URL,
            params={
                "query.bibliographic": query,
                "rows": rows,
                "mailto": self.mailto,
            },
            headers={
                "User-Agent": f"publication-doi-resolver/0.1 (mailto:{self.mailto})"
            },
            timeout=self.timeout,
        )
        response.raise_for_status()

        payload = response.json()
        return payload.get("message", {}).get("items", [])
