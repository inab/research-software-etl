import json
import random
import pytest
from src.application.services.integration.disambiguation.disambiguator import disambiguate_blocks
from tests.application.services.integration.data.data_disambiguation_original import conflicts_blocks_sets, expected, expected_heuristics
from pprint import pprint
from dotenv import load_dotenv
import os 

load_dotenv(".env") 

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
print(f"GITHUB_TOKEN: {GITHUB_TOKEN}")

with open('tests/application/services/integration/data/grouped_entries_no_opeb_test.json') as f:
    blocks = json.load(f)

@pytest.mark.asyncio
async def test_real_conflict_cases(monkeypatch):
    '''
    This test passes five different conflict cases to the disambiguation pipeline.
    The disambiguation runs for a set of blocks (blocks), which can be conflictive or not (if they are in conflicts_blocks or not)
    Thus, for each set of conflicts tested, all the blocks in blocks are processed and the conflictive blocks are disambiguated.
    '''
    # ------------ MOCKS -----------------
    # --- Mock decision_agreement_proxy so we can test pipeline without API calls ---
    def mock_decision_agreement_proxy(messages):
        # Simulate decisions based on content length or ID presence
        # random number for deciding whether disagreement or not
        print('Mock decision_agreement_proxy called')

        return {"verdict": "different", "confidence": "high"}
    
    monkeypatch.setattr("src.application.services.integration.disambiguation.disambiguator.decision_agreement_proxy", mock_decision_agreement_proxy)

    def mock_create_github_issue(title, body, labels):
        # Simulate issue creation
        print("Mock issue creation called")
        print(f"Mock issue created: {title}")
        return "Mock issue created"
    
    monkeypatch.setattr("src.application.services.integration.disambiguation.disambiguator.create_github_issue", mock_create_github_issue)

    # ------------ END MOCKS -----------------

    print(f"Instances in ale/cmd block: {len(blocks['ale/cmd']['instances'])}")
    for i, conflicts_blocks in enumerate(conflicts_blocks_sets):

        disamb_result = await disambiguate_blocks(conflicts_blocks, blocks, disambiguated_blocks_path='tests/application/services/integration/data/disambiguated_blocks.jsonl')

        # --- Assertions ---

        assert "ale/cmd" in disamb_result.keys()
        pprint(disamb_result)

        # ---- ale/cmd conflict results -----
        expected_result = expected[i]
        assert set(disamb_result['ale/cmd']['merged_entries']) == set(expected_result['merged_entries'])
        assert set(disamb_result['ale/cmd']['unmerged_entries']) == set(expected_result['unmerged_entries'])
        assert disamb_result["ale/cmd"]["resolution"] == expected_result["resolution"]
        assert disamb_result["ale/cmd"]["notes"] == expected_result["notes"]

        # ---- other results --------
        for id in ['1000genomes_vcf2ped/web', 'mapcaller/cmd', 'cvinspector/cmd']:
            assert set(disamb_result[id]['merged_entries']) == set(expected_heuristics[id]['merged_entries'])
            assert set(disamb_result[id]['unmerged_entries']) == set(expected_heuristics[id]['unmerged_entries'])
            assert disamb_result[id]["resolution"] == expected_heuristics[id]["resolution"]
            assert disamb_result[id]["source"] == expected_heuristics[id]["source"]
            assert disamb_result[id]["notes"] == expected_heuristics[id]["notes"]

        print("===" * 20)


async def test_real_conflict_cases_human(monkeypatch):
    '''
    This test passes five different conflict cases to the disambiguation pipeline.
    The disambiguation runs for a set of blocks (blocks), which can be conflictive or not (if they are in conflicts_blocks or not)
    Thus, for each set of conflicts tested, all the blocks in blocks are processed and the conflictive blocks are disambiguated.
    '''
    # --- Mock decision_agreement_proxy so we can test pipeline without API calls ---
    def mock_decision_agreement_proxy(messages):
        # Simulate decisions based on content length or ID presence
        # random number for deciding whether disagreement or not
        print('Mock decision_agreement_proxy called')
        rnd = random.random()  # generates a float between 0.0 and 1.0
        if rnd > 0.5:
            return {"verdict": "disagreement", "confidence": "high"}
        return {"verdict": "disagreement", "confidence": "high"}
    
    monkeypatch.setattr("src.application.services.integration.disambiguation.disambiguator.decision_agreement_proxy", mock_decision_agreement_proxy)

    def mock_create_github_issue(title, body, labels):
        # Simulate issue creation
        print("Mock issue creation called")
        print(f"Mock issue created: {title}")
        return "Mock issue created"
    
    monkeypatch.setattr("src.application.services.integration.disambiguation.disambiguator.create_github_issue", mock_create_github_issue)


    print(f"Instances in ale/cmd block: {len(blocks['ale/cmd']['instances'])}")
    for conflicts_blocks in conflicts_blocks_sets[0:1]:

        disamb_result = await disambiguate_blocks(conflicts_blocks, blocks, disambiguated_blocks_path='tests/application/services/integration/data/disambiguated_blocks.jsonl')

        # --- Assertions ---

        assert "ale/cmd" in disamb_result.keys()
        pprint(disamb_result["ale/cmd"])
        print("===" * 20)

