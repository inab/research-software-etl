import pytest
import os
import json
from pymongo import MongoClient  # Use pymongo or mongomock as per your preference
from src.infrastructure.db.mongo_adapter import MongoDBAdapter

@pytest.fixture(scope="module")
def db_adapter():
    client = MongoClient()  # Using a real MongoDB instance or mongomock
    db = client['test_database']

    # Load test data from JSON
    data_path = os.path.join(os.path.dirname(__file__), 'data', 'test_data.json')
    with open(data_path, 'r') as file:
        test_data = json.load(file)
    
    # Insert data into the test database
    db['alambique'].insert_many(test_data)

    # Yield the database adapter configured to use the test database
    yield MongoDBAdapter(database=db)

    # Cleanup: drop the test database
    client.drop_database('test_database')

def test_transform_workflow(db_adapter):
    from src.core.use_cases.data_transformation import transform
    import logging

    # Run the transformation process
    transform(logging.DEBUG, ['biotools', 'bioconda'], db_adapter=db_adapter)

    # Verify that the data was processed correctly
    processed_data = list(db_adapter.db['pretools'].find())
    assert len(processed_data) == 2
    assert [d['source'] for d in processed_data] == ['biotools', 'bioconda']
