from application.use_cases.integration.merge_entries import merge_and_save_blocks
import pytest


@pytest.mark.manual
def test_merge_and_save_blocks(monkeypatch):
    """
    Requires a live pretoolsDev collection: merge_entries() fetches every entry
    id from the database via fetch_entry_from_db(). Run with `pytest -m manual`.

    Writes are mocked out below -- do not remove that patch, or a run will insert
    real documents into the tools collection.
    """
    # Test the function with a sample file
    disambiguated_blocks_file = 'tests/application/use_cases/integration/data/disambiguated_blocks_2.jsonl'

    def mock_save_entry(metadata):
        print(' ------ Mock save_entries called ------- ')
        return "mocked_id"

    # NB: the module path must NOT be prefixed with "src." -- the package is
    # installed as `application.*`, so "src.application.*" patches a different
    # module object and the real save_entry would run against the database.
    monkeypatch.setattr(
        "application.use_cases.integration.merge_entries.save_entry", mock_save_entry
    )

    summary = merge_and_save_blocks(disambiguated_blocks_file)

    assert summary['N'] == 6
    assert summary['n_processed'] == 4 
    assert summary['n_inserted_entries'] == 5
    assert summary['n_pending'] == 1
    assert summary['n_unclear'] == 1


