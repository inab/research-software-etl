'''
Test the metadata entity
'''

import pytest
from pydantic import BaseModel, Field
from typing import Any

from src.core.domain.entities.metadata.pretools import Metadata
from src.core.domain.entities.metadata.pretools import source_item


# Example test data
test_data = [
    ({
        "created_at": "2023-01-01T00:00:00Z",
        "created_by": "https://gitlab.bsc.es/inb/elixir/software-observatory/bioconductor-imoprter-v2/-/commit/180347cb5bae6b553663a670a560e13c40f1e64f",
        "created_logs": "https://example.com/creation-logs",
        "last_updated_at": "2023-02-01T12:00:00Z",
        "updated_by": "https://gitlab.bsc.es/inb/elixir/software-observatory/bioconductor-imoprter-v2/-/commit/180347cb5bae6b553663a670a560e13c40f1e64f",
        "updated_logs": "https://example.com/update-logs",
        "source": {
            "collection": "tools",
            "id": "toolshed/trimal/cmd/1.4"
        }
    }, True),
    # Add test cases for invalid data
    ({
        "created_at": "2023-01-01T00:00:00",
        "created_by": "Unknown",
        "created_logs": "Not a URL",
        "last_updated_at": "Not a datetime",
        "updated_by": "Anonymous",
        "updated_logs": "Still not a URL",
        "source": {
            "collection": "tools",
            "id": 12345  # Incorrect type
        }
    }, False)
]

@pytest.mark.parametrize("input_data, expected", test_data)
def test_metadata_model_initialization(input_data, expected):
    if expected:
        # Should initialize correctly
        metadata = Metadata(**input_data)
        assert metadata.created_at == input_data['created_at']
    else:
        # Should raise a validation error
        with pytest.raises(ValueError):
            Metadata(**input_data)

def test_to_dict_for_db_insertion():
    metadata = Metadata(
        created_at="2023-01-01T00:00:00Z",
        created_by="https://gitlab.bsc.es/inb/elixir/software-observatory/bioconductor-imoprter-v2/-/commit/180347cb5bae6b553663a670a560e13c40f1e64f",
        created_logs="https://example.com/creation-logs",
        last_updated_at="2023-02-01T12:00:00Z",
        updated_by="https://gitlab.bsc.es/inb/elixir/software-observatory/bioconductor-imoprter-v2/-/commit/180347cb5bae6b553663a670a560e13c40f1e64f",
        updated_logs="https://example.com/update-logs",
        source=source_item(collection="tools", id="toolshed/trimal/cmd/1.4")
    )
    result = metadata.to_dict_for_db_insertion()
    # Check for correct keys and values
    for key, value in result.items():
        assert key.startswith('@')
        assert result[key] == getattr(metadata, key[1:])
