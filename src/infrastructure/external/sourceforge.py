from __future__ import annotations

import logging
import random
import time

import requests

logger = logging.getLogger("rs-etl-pipeline")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SourceForgeMetadataImporter/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
}


class SourceForgeClient:
    """
    Fetches SourceForge project pages.

    SourceForge sits behind Cloudflare and rate-limits hard, so the retry and
    backoff below are not incidental -- they are the only reason a project page
    comes back at all. That is transport, and it belongs here rather than in the
    service that parses the HTML.
    """

    def __init__(
        self,
        max_retries: int = 5,
        base_delay: int = 10,
        timeout: int = 30,
    ) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.timeout = timeout

        self._session = requests.Session()
        self._session.headers.update(HEADERS)

    def fetch_html(self, url: str) -> str | None:
        """The page's HTML, or None if SourceForge never served it."""
        for attempt in range(self.max_retries):
            try:
                response = self._session.get(url, timeout=self.timeout)
                logger.info(f"SourceForge GET {url} -> {response.status_code}")
            except requests.RequestException as e:
                logger.warning(f"SourceForge request failed for {url}: {e}")
                self._back_off(attempt, jitter=2)
                continue

            if response.status_code == 200:
                html = response.text
                if (
                    "Just a moment..." in html
                    or "Enable JavaScript and cookies to continue" in html
                ):
                    logger.warning(
                        f"SourceForge returned Cloudflare challenge page for {url}"
                    )
                    self._back_off(attempt, jitter=5)
                    continue
                return html

            if response.status_code in (403, 429, 503):
                logger.warning(
                    f"SourceForge returned {response.status_code} for {url} "
                    f"(attempt {attempt + 1}/{self.max_retries})."
                )
                self._back_off(attempt, jitter=5)
                continue

            if response.status_code == 404:
                logger.warning(f"SourceForge returned 404 for {url}")
                return None

            logger.warning(
                f"Unexpected SourceForge status {response.status_code} for {url}"
            )
            return None

        return None

    def _back_off(self, attempt: int, jitter: int) -> None:
        sleep_time = self.base_delay * (2**attempt) + random.uniform(0, jitter)
        logger.info(f"Sleeping {sleep_time:.2f}s before retry")
        time.sleep(sleep_time)
