import pytest
from application.use_cases.integration.merge_entries import fetch_entry_from_db


@pytest.mark.manual
def test_fetch_entry_from_db():
    """Requires a live pretoolsDev collection. Run with `pytest -m manual`."""
    id = 'bioconda_recipes/ale/cmd/20180904'
    entry = fetch_entry_from_db(id)

    assert entry is not None, f"{id} not found in pretools"
    assert entry["_id"] == id
    assert "data" in entry