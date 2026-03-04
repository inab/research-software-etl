from src.application.services.integration.disambiguation.utils import stable_hash
import pytest


def test_pair_stable_hash():

    conflict_pair_A = {
        'disconnected': [{'_id':'biotools/arboreto/undefined/0.1.5'}],
        'remaining' : [{'_id':'github/arboreto/None/None,bioconda_recipes/arboreto/lib/0.1.6'}]
    }

    conflict_pair_B = {
        'disconnected': [{'_id':'biotools/arboreto/undefined/0.1.5'}],
        'remaining' : [{'_id':'bioconda_recipes/arboreto/lib/0.1.6,github/arboreto/None/None'}]
    }

    assert stable_hash(conflict_pair_A) == stable_hash(conflict_pair_B)