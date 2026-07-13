import pytest
from freezegun import freeze_time
from pydantic import HttpUrl
from application.services.transformation.metadata import create_new_metadata, update_existing_metadata, build_commit_url
from domain.models.metadata import Metadata
from infrastructure.config import CIContext


# Provenance is now injected rather than read from the environment.
@pytest.fixture
def ci():
    return CIContext(
        project_namespace="project_namespace",
        project_name="project_name",
        commit_sha="commit_sha",
        pipeline_url="https://pipeline.url",
    )


# Using freezegun to freeze the datetime
@freeze_time("2023-01-01T12:00:00")
def test_create_new_metadata(ci):
    identifier = "001"
    source_id = "002"
    alambique = "tools"
    source_url = "https://github.com"
    metadata = create_new_metadata(source_id, identifier, source_url, alambique, ci)

    assert metadata.created_at == "2023-01-01T12:00:00"
    assert metadata.created_by == build_commit_url(ci)
    assert metadata.created_logs == "https://pipeline.url"
    assert metadata.last_updated_at == "2023-01-01T12:00:00"
    assert metadata.updated_by == build_commit_url(ci)
    assert metadata.updated_logs == "https://pipeline.url"
    assert metadata.source[0].collection == alambique
    assert metadata.source[0].id == source_id
    assert metadata.source[0].source_url == HttpUrl(source_url)


@freeze_time("2023-01-01T12:00:00")
def test_update_existing_metadata(ci):
    alambique = "tools"
    source_url = "https://github.com"
    existing_metadata = Metadata(
        id="001",
        created_at="2022-12-25T12:00:00",
        created_by="https://old.url",
        created_logs="https://old.pipeline.url",
        last_updated_at="2022-12-25T12:00:00",
        updated_by="https://old.url",
        updated_logs="https://old.pipeline.url",
        source=[{"collection": alambique, "id": "002", "source_url": source_url}]
    )

    updated_metadata = update_existing_metadata(existing_metadata, ci)

    assert updated_metadata.last_updated_at == "2023-01-01T12:00:00"
    assert updated_metadata.updated_by == build_commit_url(ci)
    assert updated_metadata.updated_logs == "https://pipeline.url"
    assert updated_metadata.created_at == "2022-12-25T12:00:00"  # Should remain unchanged
    assert updated_metadata.created_by == "https://old.url"  # Should remain unchanged


def test_commit_url_falls_back_outside_ci():
    """With no CI vars, provenance must not read 'gitlab.bsc.es/None/None/-/commit/None'."""
    url = build_commit_url(CIContext())

    assert "None" not in url
    assert url == CIContext().fallback_commit_url
