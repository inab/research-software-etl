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

@pytest.mark.manual
@pytest.mark.asyncio
async def test_full_disambiguation_with_github_issue(monkeypatch):
    blocks_file = 'tests/application/use_cases/integration/data/blocks.json'
    conflict_blocks_file = 'tests/application/use_cases/integration/data/conflict_blocks.json'
    disambiguated_blocks_file = 'tests/application/use_cases/integration/data/disambiguated_blocks.json'


    # Mock the decision proxy to force manual disambiguation. Copy from the service test.

    # --- Mock decision_agreement_proxy so we can test pipeline without API calls ---
    def mock_decision_agreement_proxy(messages):
        # Simulate decisions based on content length or ID presence
        print(' ------ Mock decision_agreement_proxy called ------- ')
        return {"verdict": "disagreement", "confidence": "high"}
    
    monkeypatch.setattr("src.application.services.integration.disambiguation.disambiguator.decision_agreement_proxy", mock_decision_agreement_proxy)


    # Run the full disambiguation process
    await run_full_disambiguation(blocks_file, conflict_blocks_file, disambiguated_blocks_file)

    # Load the results
    with open(disambiguated_blocks_file, 'r') as f:
        disambiguated_blocks = json.load(f)

    # Check if the disambiguated blocks are as expected
    assert "ale/cmd" in disambiguated_blocks.keys()

