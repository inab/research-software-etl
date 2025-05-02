from src.application.services.integration.disambiguation import build_pairs 
from tests.application.services.integration.data.data_disambiguation_build_pairs import conflict_full_entries, original_key
from pprint import pprint

class TestBuildPairs:

    def test_build_pairs(self):
        """       
        """
        more_than_two_pairs = 0

        pair_conflict, more_than_two_pairs = build_pairs(conflict_full_entries, original_key, more_than_two_pairs)
        # pretty print the result
        print('--'*20)
        print(f"Number of entries in disconnected: {len(conflict_full_entries['disconnected'])}")
        print(f"Number of entries merged to build the remaining entry: {len(pair_conflict)}")
        #print(f"IDs of remaining entries: {ids_remaining}")
        print(f"Number of pairs with more than two entries: {more_than_two_pairs}")
        print('--'*20)
        print(f"Merged entry:\n")
        pprint(pair_conflict['remaining'][0])
        print('--'*20)
        print(f"Disconnected entry:\n")
        pprint(pair_conflict['disconnected'][0])

        # Check the structure of the pair_conflict dictionary
        assert isinstance(pair_conflict, dict)
        


        
        