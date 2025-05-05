import json
import random
import pytest
from src.application.services.integration.disambiguation.disambiguator import disambiguate_blocks
from src.application.services.integration.disambiguation.secondary_round import generate_secondary_conflicts
from tests.application.services.integration.data.data_disambiguation_original import conflicts_blocks_sets, expected, expected_heuristics
from pprint import pprint
from dotenv import load_dotenv
import os 

load_dotenv(".env") 

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
print(f"GITHUB_TOKEN: {GITHUB_TOKEN}")

with open('tests/application/services/integration/data/grouped_entries_no_opeb_test.json') as f:
    blocks = json.load(f)



disambiguated_first_round = {
    '1000genomes_vcf2ped/web': {'confidence_scores': {},
                             'merged_entries': ['biotools/1000genomes_vcf2ped/web/1'],
                             'notes': 'All entries grouped heuristically or by '
                                      'shared metadata. No disambiguation '
                                      'needed.',
                             'resolution': 'no_conflict',
                             'source': 'auto:no_conflict',
                             'timestamp': '2025-05-05T10:31:54.368635',
                             'unmerged_entries': []},
 'ale/cmd': {'confidence_scores': {'bioconda_recipes/ale/cmd/20180904': 'high',
                                   'biotools/ale/cmd/None': 'high'},
             'merged_entries': ['bioconda_recipes/ale-core/cmd/20220503'],
             'notes': None,
             'resolution': 'partial',
             'source': 'auto:agreement-proxy-v',
             'timestamp': '2025-05-05T10:32:17.837414',
             'unmerged_entries': ['biotools/ale/cmd/None',
                                  'bioconda_recipes/ale/cmd/20180904']},
 'cvinspector/cmd': {'confidence_scores': {},
                     'merged_entries': ['galaxy/cvinspector/cmd/2.3.0',
                                        'galaxy_metadata/cvinspector/cmd/2.2.0',
                                        'toolshed/cvinspector/cmd/2.2.0'],
                     'notes': 'All entries grouped heuristically or by shared '
                              'metadata. No disambiguation needed.',
                     'resolution': 'no_conflict',
                     'source': 'auto:no_conflict',
                     'timestamp': '2025-05-05T10:32:17.837459',
                     'unmerged_entries': []},
 'mapcaller/cmd': {'confidence_scores': {},
                   'merged_entries': ['bioconda_recipes/mapcaller/cmd/0.9.9.41',
                                      'biotools/mapcaller/cmd/None',
                                      'github/MapCaller/None/v0.9.9.d'],
                   'notes': 'All entries grouped heuristically or by shared '
                            'metadata. No disambiguation needed. Caution: '
                            'merged entries have different names — may be '
                            'distinct software.',
                   'resolution': 'no_conflict',
                   'source': 'auto:no_conflict',
                   'timestamp': '2025-05-05T10:32:17.837449',
                   'unmerged_entries': []}}


@pytest.mark.asyncio
async def test_secondary_round(monkeypatch):
    """
    """
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
    conflict_blocks = conflicts_blocks_sets[2] # two disconnected and one connected
    disambiguated_blocks = disambiguated_first_round
    assert "ale/cmd" in disambiguated_blocks.keys()
    print("============= Disambiguation result for secondary round ==========================")
    secondary_conflict, secondary_block = generate_secondary_conflicts(disambiguated_blocks)
    print("secondary_conflict:")
    pprint(secondary_conflict)
    print("======================== secondary blocks created ==================================")
    assert len(secondary_conflict) == 1
    conflict_blocks.update(secondary_conflict)
    blocks.update(secondary_block)

    print(f"Conflict blocks: {conflict_blocks}")
    print(f"Blocks: {blocks}")
    disambiguated_blocks = await disambiguate_blocks(conflict_blocks, blocks, disambiguated_blocks_path='tests/application/services/integration/data/disambiguated_blocks_first_round.json')
    pprint(disambiguated_blocks)
    unresolved_keys = [k for k in conflict_blocks if k not in disambiguated_blocks]
    print(f"Unresolved keys: {unresolved_keys}")
    print("======================== second round completed =============================")
    assert not unresolved_keys

    



