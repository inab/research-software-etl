from __future__ import annotations

from dataclasses import dataclass

from infrastructure.config import Credentials
from infrastructure.external.github import GitHubClient
from infrastructure.external.gitlab import GitLabClient
from infrastructure.external.huggingface import HuggingFaceClient
from infrastructure.external.openrouter import OpenRouterClient


@dataclass(frozen=True)
class ExternalClients:
    """
    The external services the disambiguation stage talks to.

    Built once at the CLI from a :class:`Credentials` and passed down the
    disambiguation chain, so nothing below ``adapters/`` has to reach for a
    token. Tests construct this with fakes instead of patching module globals.
    """

    openrouter: OpenRouterClient
    huggingface: HuggingFaceClient
    github: GitHubClient
    gitlab: GitLabClient

    @classmethod
    def from_credentials(cls, credentials: Credentials) -> "ExternalClients":
        return cls(
            openrouter=OpenRouterClient(credentials.openrouter_api_key),
            huggingface=HuggingFaceClient(credentials.huggingface_api_key),
            github=GitHubClient(credentials.github_token),
            gitlab=GitLabClient(credentials.gitlab_token),
        )
