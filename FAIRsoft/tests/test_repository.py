from FAIRsoft.classes.repository import repository_item, repository_kind
from pydantic import HttpUrl
import pytest


class TestRepositoryItem:

    # Creating a repository_item object with a valid URL and no other parameters should succeed.
    def test_valid_url_no_parameters(self):
        url = "https://github.com/example/repository"
        item = repository_item(url=url)

        assert item.url == HttpUrl(url)
        assert item.kind is repository_kind.github
        assert item.source_hasAnonymousAccess is None
        assert item.source_isDownloadRegistered is None
        assert item.source_isFree is None
        assert item.source_isRepoAccessible is None

    # Creating a repository_item object with a valid URL and valid parameters should succeed.
    def test_valid_url_valid_parameters(self):
        url = "https://github.com/example/repository"
        kind = 'github'
        has_anonymous_access = True
        is_download_registered = True
        is_free = True
        is_repo_accessible = True

        item = repository_item(url=url, 
                               kind=kind, 
                               source_hasAnonymousAccess=has_anonymous_access,
                               source_isDownloadRegistered=is_download_registered, 
                               source_isFree=is_free,
                               source_isRepoAccessible=is_repo_accessible)

        assert item.url == HttpUrl(url)
        assert item.kind == repository_kind.github
        assert item.source_hasAnonymousAccess == has_anonymous_access
        assert item.source_isDownloadRegistered == is_download_registered
        assert item.source_isFree == is_free
        assert item.source_isRepoAccessible == is_repo_accessible

    # Creating a repository_item object with a valid URL and invalid parameters should raise an error
    def test_valid_url_invalid_parameters(self):
        url = "https://github.com/example/repository"
        kind = "invalid_kind"
        has_anonymous_access = "invalid_value"
        is_download_registered = "invalid_value"
        is_free = "invalid_value"
        is_repo_accessible = "invalid_value"

        with pytest.raises(ValueError):
            repository_item(url=url, 
                            kind=kind, 
                            source_hasAnonymousAccess=has_anonymous_access,
                            source_isDownloadRegistered=is_download_registered, 
                            source_isFree=is_free,
                            source_isRepoAccessible=is_repo_accessible)

    # Creating a repository_item object with an invalid URL should raise a validation error.
    def test_invalid_url(self):
        url = "invalid_url"

        with pytest.raises(ValueError):
            repository_item(url=url)

    # Creating a repository_item object with a valid URL and an invalid kind parameter should raise a validation error
    def test_valid_url_invalid_kind_parameter(self):
        url = "https://github.com/example/repository"
        kind = "invalid_kind"

        with pytest.raises(ValueError):
            repository_item(url=url, kind=kind)

    # Creating a repository_item object with a valid URL and invalid boolean parameters should raise a validation error
    def test_valid_url_invalid_boolean_parameters(self):
        url = "https://github.com/example/repository"
        has_anonymous_access = "invalid_value"
        is_download_registered = "invalid_value"
        is_free = "invalid_value"
        is_repo_accessible = "invalid_value"

        with pytest.raises(ValueError):
            repository_item(url=url, 
                            source_hasAnonymousAccess=has_anonymous_access,
                            source_isDownloadRegistered=is_download_registered, 
                            source_isFree=is_free,
                            source_isRepoAccessible=is_repo_accessible)

        