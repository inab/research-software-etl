import pytest
import os
import json
from pymongo import MongoClient  # Use pymongo or mongomock as per your preference
from src.infrastructure.db.mongo_adapter import MongoDBAdapter

@pytest.fixture(scope="module")
def db_adapter():
    client = MongoClient()  # Using a real MongoDB instance or mongomock
    db = client['test_database']
    client.drop_database('test_database')
    db = client['test_database']

    # Load test data from JSON
    data_path = './tests/core/use_cases/data/merged_data.json'
    with open(data_path, 'r') as file:
        test_data = json.load(file)
    
    # Insert data into the test database
    db['alambique'].insert_many(test_data)

    # Yield the database adapter configured to use the test database
    yield MongoDBAdapter(database='test_database')

    # Cleanup: drop the test database
    client.drop_database('test_database')

def test_transform_workflow(db_adapter):
    from src.core.use_cases.data_transformation import transform
    import logging

    # Run the transformation process
    sources = [
        'biotools',
        'bioconda',
        'bioconda_recipes',
        'bioconductor',
        'galaxy_metadata',
        'toolshed',
        'galaxy',
        'sourceforge',
        'opeb_metrics'
    ]
    transform(logging.DEBUG, sources, db_adapter=db_adapter)

    # Verify that the data was processed correctly
    processed_data = list(db_adapter.fetch_entries('pretools', {}))
    assert len(processed_data) == 90
    assert [d['@source'] for d in processed_data] == sources
