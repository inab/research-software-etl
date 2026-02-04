from tests.application.services.integration.data.data_disambiguation_build_pairs import conflict_full_entries_one_two, conflict_full_entries_one_one, conflict_full_entries_two_one, original_key
from src.application.services.integration.disambiguation.utils import stable_hash, load_pair_decisions
from datetime import datetime, timezone
from random import  uniform

from pprint import pprint
import random
import copy
import json
import pytest


def append_pair_decision(path, decision: dict):
    """
    Append a single pair decision to the JSONL ledger.
    """
    with open(path, "a") as f:
        f.write(json.dumps(decision, ensure_ascii=False) + "\n")



def test_create_test_data():

    PAIRS_PATH = '/Users/evabsc/projects/software-observatory/research-software-etl/tests/application/services/integration/data/test_pair_decisions.jsonl'

    conflicts = [conflict_full_entries_one_two, conflict_full_entries_one_one, conflict_full_entries_two_one]   
    # 
    '''
    conflicts = []

    for n in range(5):
        conflict_name = original_key
        conflict_pairs, _  = build_pairs(copy.deepcopy(conflict_full_entries_one_two), conflict_name, more_than_two_pairs=0)
        for conflict_pair in conflict_pairs:
            pair_id = f"p:{stable_hash(conflict_pair)}"
            file = f"/Users/evabsc/projects/software-observatory/research-software-etl/tests/application/services/integration/data/{pair_id}.json"

            with open(file, 'w') as f:
                json.dump(conflict_pair, f, indent=4)
            
            print(f"\nRun {n}: {pair_id}\n")

            conflicts.append(conflict_pair)
        
    assert conflicts[0] == conflicts[1]
    '''
'''
    for conflict in conflicts:
        conflict_name = original_key
        conflict_pairs, _  = build_pairs(copy.deepcopy(conflict), conflict_name, more_than_two_pairs=0)
        #pprint(conflict_pairs)
        
        for conflict_pair in conflict_pairs:

            pair_id = f"p:{conflict_name}_{stable_hash(conflict_pair)}"
            print(f"\n{pair_id}\n")
            decision = {
                'pair_id': pair_id,
                'kind': 'pair',
                'same_as_remaining': bool(random.getrandbits(1)),
                'confidence': round(uniform(.6, 1.0), 2),
                'source': 'llm',
                'ts':datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                'disconnected_id': [item['_id'] for item in conflict_pair['disconnected']],
                'remaining_id': [item['_id'] for item in conflict_pair['remaining']]
            }

            append_pair_decision(PAIRS_PATH, decision)
'''



        

def test_basic_cache_hit(): 

    PAIRS_PATH = '/Users/evabsc/projects/software-observatory/research-software-etl/tests/application/services/integration/data/test_pair_decisions.jsonl'

    best_pair = load_pair_decisions(PAIRS_PATH)
    #print(f"\n{best_pair}\n")

    test_pair_id = "p:antarna/cmd_29b5b1ef512f8a7757dbcfd548621f63c8502e16cc661a8a8d4e42480b078f7d"

    assert test_pair_id in best_pair


def test_override_human():
    'Human decision is preferred'
    pair_id = 'p:antarna/cmd_71e0720995929eb2c1adc11525c5de27969813e710337254cb96e70ac851834f'
    PAIRS_PATH = '/Users/evabsc/projects/software-observatory/research-software-etl/tests/application/services/integration/data/test_pair_decisions.jsonl'

    best_pair = load_pair_decisions(PAIRS_PATH)

    assert best_pair[pair_id]['source'] == 'human'


def test_latest_preferred():
    pair_id = 'p:antarna/cmd_bb865b4321428526d1a23d4f1d630a33cf6945a76267eddd0f70dbf2e1f1a193'
    PAIRS_PATH = '/Users/evabsc/projects/software-observatory/research-software-etl/tests/application/services/integration/data/test_pair_decisions.jsonl'
    best_pair = load_pair_decisions(PAIRS_PATH)

    assert best_pair[pair_id]['source'] == 'llm'
    assert best_pair[pair_id]['ts'] == '2026-02-02T16:12:40Z'





