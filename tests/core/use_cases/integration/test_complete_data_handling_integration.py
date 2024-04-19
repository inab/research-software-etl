import pytest
from mongomock import MongoClient
from src.infrastructure.db.mongo_adapter import MongoDBAdapter
from src.core.domain.services.transformation.standardizers_factory import StandardizersFactory
from src.core.domain.entities.metadata.pretools import Metadata
from src.core.use_cases.data_transformation import generate_metadata, standardize_entry


@pytest.fixture
def mongo_db():
    client = MongoClient()
    db = client['test_db']
    yield db
    client.drop_database('test_db')

@pytest.fixture
def db_adapter(mongo_db):
    return MongoDBAdapter(database=mongo_db)

def test_complete_data_handling(db_adapter):
    # Setup test data in the database
    collection_name = 'raw_entries'
    test_data = [{'_id': '123', 'data': 'sample'}]
    db_adapter.db[collection_name].insert_many(test_data)

    # Process each entry (mocking the process_entry function behavior here)
    for entry in db_adapter.db[collection_name].find():
        identifier = entry['_id']
        standardized_entries = standardize_entry(entry, 'test_source')  # Assume it returns list of entries
        metadata = generate_metadata(identifier, db_adapter)

        for std_entry in standardized_entries:
            update_document = metadata.to_dict_for_db_insertion()
            update_document['data'] = std_entry
            db_adapter.update_entry('processed_data', identifier, update_document)

    # Verify that processed data is updated correctly
    updated_entry = db_adapter.db['processed_data'].find_one({'_id': '123'})
    assert updated_entry is not None
    assert 'data' in updated_entry
