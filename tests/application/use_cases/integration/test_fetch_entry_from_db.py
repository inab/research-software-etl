import pytest 
from src.application.use_cases.integration.merge_entries import fetch_entry_from_db

def test_fetch_entry_from_db():
    id = 'bioconda_recipes/ale/cmd/20180904'
    entry = fetch_entry_from_db(id)
    print(entry)