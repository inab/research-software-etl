import pytest
from mongomock import MongoClient
from src.infrastructure.db.mongo_adapter import MongoDBAdapter
from src.core.domain.services.transformation.standardizers_factory import StandardizersFactory
from src.core.use_cases.data_transformation import get_raw_data_db, standardize_entry              

@pytest.fixture
def mongo_db():
    client = MongoClient()
    db = client['test_db']
    yield db
    client.drop_database('test_db')

@pytest.fixture
def db_adapter(mongo_db):
    return MongoDBAdapter(database=mongo_db)

def test_data_retrieval_and_processing(db_adapter):
    # Insert mock data into the database
    collection_name = 'test_data'
    test_data = [{'_id': '1', 'data': 'info1'}, {'_id': '2', 'data': 'info2'}]
    db_adapter.db[collection_name].insert_many(test_data)

    # Retrieve and process data
    raw_data = get_raw_data_db('test_source', db_adapter)
    processed_data = [standardize_entry(data, 'test_source') for data in raw_data]

    # Assertions to check if the data is processed correctly
    assert len(processed_data) == len(test_data)
    assert all(isinstance(item, list) for item in processed_data)  # Assuming the output is a list of dicts

    # Further checks can be added to verify the content of processed_data
