from src.application.use_cases.integration.disambiguation import run_full_disambiguation
import pytest
import json



# ------- WARNING ------------------
# This test creates an issue in the research-software-etl repository.
# It is recommended to run it only once and check the results.
# To run manual tests, use the command:
# pytest -m manual
# ------- END WARNING --------------

@pytest.mark.manual
@pytest.mark.asyncio
async def test_full_disambiguation():
    """
    Test the full disambiguation process, including loading data, running disambiguation,
    and saving results.
    """
    blocks_file = 'tests/application/use_cases/integration/data/blocks.json'
    conflict_blocks_file = 'tests/application/use_cases/integration/data/conflict_blocks.json'
    disambiguated_blocks_file = 'tests/application/use_cases/integration/data/disambiguated_blocks.json'

    # Run the full disambiguation process
    await run_full_disambiguation(blocks_file, conflict_blocks_file, disambiguated_blocks_file)

    # Load the results
    with open(disambiguated_blocks_file, 'r') as f:
        disambiguated_blocks = json.load(f)

    # Check if the disambiguated blocks are as expected
    assert "ale/cmd" in disambiguated_blocks.keys()