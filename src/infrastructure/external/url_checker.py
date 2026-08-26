from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Iterable, Iterator, Tuple

import requests

logger = logging.getLogger("rs-etl-pipeline")

DEFAULT_TIMEOUT = 15
DEFAULT_USER_AGENT = "oeb-research-software-etl/1.0 (+monitor)"
DEFAULT_MAX_WORKERS = 32


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
        max_workers: int = DEFAULT_MAX_WORKERS,
    ) -> None:
        self.timeout = timeout
        self.max_workers = max_workers
        self._user_agent = user_agent
        # One Session per thread: ``requests.Session`` is not thread-safe (shared
        # connection pool and cookie jar), so ``probe_many`` cannot share one across
        # its workers. A ``threading.local`` gives each worker its own, lazily, while
        # a single-threaded caller still reuses one Session for the whole run.
        self._local = threading.local()

    @property
    def _session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            session.headers.update({"User-Agent": self._user_agent, "Accept": "*/*"})
            self._local.session = session
        return session

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

    def probe_many(
        self,
        urls: Iterable[str],
        timeout: int | None = None,
        max_workers: int | None = None,
    ) -> Iterator[Tuple[str, UrlProbe]]:
        """
        Probe many URLs concurrently, yielding ``(url, UrlProbe)`` as each finishes.

        Probing is almost entirely idle network waiting -- most of the sweep is
        spent timing out on unreachable hosts, one at a time when done serially --
        so fanning it out across a thread pool collapses the wall-clock cost. Results
        arrive in completion order, not input order; the caller keys each reading by
        its own URL, so order does not matter. Each URL is a distinct document with
        one reading per run, so nothing downstream depends on the sequence either.

        ``probe`` swallows every per-URL error into ``UrlProbe(None, None)``, so a
        worker never raises and one bad URL cannot sink the batch.
        """
        workers = max_workers or self.max_workers
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(self.probe, url, timeout): url for url in urls}
            for future in as_completed(futures):
                yield futures[future], future.result()

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
