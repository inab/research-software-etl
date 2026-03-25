from application.use_cases.integration.merge_entries import merge_and_save_blocks
import pytest
 

def test_merge_and_save_blocks(monkeypatch):
    # Test the function with a sample file
    disambiguated_blocks_file = 'tests/application/use_cases/integration/data/disambiguated_blocks_2.jsonl'

    def mock_save_entry(metadata):
        # Simulate decisions based on content length or ID presence
        print(' ------ Mock save_entries called ------- ')
        return "mocked_id"
    
    monkeypatch.setattr("src.application.use_cases.integration.merge_entries.save_entry", mock_save_entry)

    summary = merge_and_save_blocks(disambiguated_blocks_file)

    assert summary['N'] == 6
    assert summary['n_processed'] == 4 
    assert summary['n_inserted_entries'] == 5
    assert summary['n_pending'] == 1
    assert summary['n_unclear'] == 1


