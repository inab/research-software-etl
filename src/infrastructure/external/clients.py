from __future__ import annotations

from dataclasses import dataclass

from infrastructure.config import Credentials
from infrastructure.external.bitbucket import BitbucketClient
from infrastructure.external.gepeto import GepetoClient
from infrastructure.external.github import GitHubClient
from infrastructure.external.gitlab import GitLabClient
from infrastructure.external.headless_browser import HeadlessBrowserFetcher
from infrastructure.external.pypi import PyPIClient
from infrastructure.external.sourceforge import SourceForgeClient
from infrastructure.external.url_checker import UrlChecker


@dataclass(frozen=True)
class ExternalClients:
    """
    The external services the disambiguation stage talks to.

    Built once at the CLI from a :class:`Credentials` and passed down the
    disambiguation chain, so nothing below ``adapters/`` has to reach for a
    token. Tests construct this with fakes instead of patching module globals.

    Only the first three carry a token. The rest are bundled for the same reason --
    they are transport, and a service that owns its own `requests.Session` cannot
    be run offline -- and they are built without credentials.
    """

    gepeto: GepetoClient
    github: GitHubClient
    gitlab: GitLabClient
    url_checker: UrlChecker
    pypi: PyPIClient
    sourceforge: SourceForgeClient
    bitbucket: BitbucketClient
    browser: HeadlessBrowserFetcher

    @classmethod
    def from_credentials(cls, credentials: Credentials) -> "ExternalClients":
        return cls(
            gepeto=GepetoClient(credentials.gepeto_api_key),
            github=GitHubClient(credentials.github_token),
            gitlab=GitLabClient(credentials.gitlab_token),
            url_checker=UrlChecker(),
            pypi=PyPIClient(),
            sourceforge=SourceForgeClient(),
            bitbucket=BitbucketClient(),
            browser=HeadlessBrowserFetcher(),
        )
