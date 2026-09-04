from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger("rs-etl-pipeline")


class ObservatoryApiClient:
    """
    Client for the observatory API's admin operations.

    The only call the pipeline makes here is the post-promotion reindex: merge
    swaps in a freshly-built tools collection that has nothing but its default
    ``_id`` index, so the API's `/search` text index and filter indexes have to
    be rebuilt before that collection is queried. The index *definitions* live in
    the API repo (they encode its query shapes and a collation that must match
    the search route); this client only triggers them.
    """

    REINDEX_PATH = "/admin/reindex"

    def __init__(self, base_url: str, token: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token

    def ensure_tools_indexes(
        self, force_text: bool = False, timeout: float = 300.0
    ) -> dict[str, Any]:
        """
        Ask the API to (re)create the tools/stats indexes. Idempotent server-side.

        ``force_text`` drops and rebuilds the text index (needed only when its
        fields/weights change). Raises on a non-2xx response so the caller can
        log it -- by the time this runs the collection is already live, so the
        caller warns rather than failing the run.
        """
        url = f"{self.base_url}{self.REINDEX_PATH}"
        headers = {"Authorization": f"Bearer {self.token}"}
        logger.info("Requesting tools reindex: POST %s (force_text=%s)", url, force_text)

        response = requests.post(
            url, headers=headers, json={"force_text": force_text}, timeout=timeout
        )
        response.raise_for_status()
        return response.json()
