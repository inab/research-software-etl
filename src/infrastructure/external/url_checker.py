from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests

logger = logging.getLogger("rs-etl-pipeline")

DEFAULT_TIMEOUT = 15
DEFAULT_USER_AGENT = "oeb-research-software-etl/1.0 (+monitor)"


@dataclass(frozen=True)
class UrlProbe:
    """
    What one reachability check saw.

    ``status is None`` means the request never completed -- DNS failure, refused
    connection, timeout -- which is different from a server answering 404.
    """

    status: int | None
    access_time: float | None


class UrlChecker:
    """
    "Is this URL reachable, and where does it end up?"

    Three stages asked that question and each owned a `requests.Session` to do it:
    the web-availability job, GitHub redirect resolution in conflict detection, and
    link enrichment in disambiguation. None of them could run without a network, so
    the tests either reached the internet or monkeypatched a module global.

    They all go through this one seam now. It is not a client for a particular host,
    which is why it takes no token: probing arbitrary tool URLs *is* the job.
    """

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": user_agent, "Accept": "*/*"})

    def probe(self, url: str, timeout: int | None = None) -> UrlProbe:
        """
        Check whether ``url`` answers, and how long it took.

        HEAD first, then GET: a 400/403/405 to a HEAD means "not with that verb",
        not "unreachable", and plenty of the hosts we monitor say exactly that.
        """
        timeout = timeout or self.timeout

        probe = self._request("HEAD", url, timeout)
        if probe.status is None or probe.status in (400, 403, 405):
            return self._request("GET", url, timeout)

        return probe

    def resolve_redirects(self, url: str, timeout: int | None = None) -> str | None:
        """
        Follow redirects and return the URL we land on, or None if it cannot be reached.

        Callers use this to tell whether two records point at the same thing under
        different names -- a renamed GitHub repository, a shortened link.
        """
        timeout = timeout or self.timeout

        try:
            response = self._session.head(url, allow_redirects=True, timeout=timeout)
            final_url = response.url

            # Some servers do not redirect reliably on HEAD.
            if not final_url:
                response = self._session.get(
                    url, allow_redirects=True, timeout=timeout, stream=True
                )
                final_url = response.url

            return final_url or None

        except Exception as e:
            logger.debug(f"Could not resolve {url}: {e}")
            return None

    def _request(self, method: str, url: str, timeout: int) -> UrlProbe:
        start = time.perf_counter()
        try:
            response = self._session.request(
                method, url, timeout=timeout, allow_redirects=True
            )
            return UrlProbe(response.status_code, time.perf_counter() - start)
        except Exception:
            # Deliberately broad: this walks URLs from third-party registries, and a
            # malformed one must be recorded as unreachable, not abort the stage.
            return UrlProbe(None, None)
