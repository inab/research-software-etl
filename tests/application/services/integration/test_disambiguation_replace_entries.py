from src.application.services.integration.disambiguation.utils import build_instances_keys_dict, replace_with_full_entries
from tests.application.services.integration.data.data_disambiguation_original import original_conflict
import pytest 
import json
from pprint import pprint


# ---------
# build instances_keys_dict with tests/application/services/integration/data/grouped_entries.json 
# ---------

with open('tests/application/services/integration/data/grouped_entries.json') as f:
    grouped_entries = json.load(f)

instances_dict = build_instances_keys_dict(grouped_entries)

# save the instances_dict to a json file
with open('tests/application/services/integration/data/instances_dict.json', 'w') as f:
    json.dump(instances_dict, f, indent=4)


# ---------
# Test 
# ---------

class TestReplaceWithFullEntries:

    def test_replace_with_full_entries(self): 

        conflict = replace_with_full_entries(original_conflict, instances_dict)
        #pprint(conflict)
        
        assert isinstance(conflict, dict)
        
        assert len(conflict["disconnected"]) == 1
        assert len(conflict["remaining"]) == 2

        for field in ['data', 'source']:
            assert field in conflict["disconnected"][0]
            assert field in conflict["remaining"][0]
            assert field in conflict["remaining"][1]

        



