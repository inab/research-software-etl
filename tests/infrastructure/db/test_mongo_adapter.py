import pytest
from unittest.mock import patch, MagicMock
from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


# Ensure the environment variables are correctly mocked
@pytest.fixture
def mock_env_vars(mocker):
    env_vars = {
        'MONGO_HOST': 'localhost',
        'MONGO_PORT': '27017',
        'MONGO_USER': 'user',
        'MONGO_PWD': 'password',
        'MONGO_AUTH_SRC': 'admin',
        'MONGO_DB': 'oeb-research-software'
    }
    mocker.patch.dict('os.environ', env_vars)

# Mock MongoClient directly in the MongoDBAdapter scope
@pytest.fixture
def mock_mongo_client(mocker):
    with patch('pymongo.MongoClient') as mock_client:
        yield mock_client

def test_mongodb_adapter_init(mock_env_vars, mock_mongo_client):
    # Test initialization of MongoDBAdapter
    adapter = mongo_adapter
    mock_mongo_client.assert_called_once_with(
        host=['localhost:27017'],
        username='user',
        password='password',
        authSource='admin',
        authMechanism='SCRAM-SHA-256'
    )

def test_entry_exists_true(mock_env_vars, mock_mongo_client):
    # Setup
    adapter = mongo_adapter
    collection_name = 'test_collection'
    query = {'_id': 'some_id'}
    
    # Mock the count_documents method to return a non-zero value
    mock_mongo_client.return_value.__getitem__.return_value.__getitem__.return_value.count_documents.return_value = 1
    
    # Test
    assert adapter.entry_exists(collection_name, query) == True

def test_entry_exists_false(mock_env_vars, mock_mongo_client):
    # Setup
    adapter = mongo_adapter
    collection_name = 'test_collection'
    query = {'_id': 'nonexistent_id'}
    
    # Mock the count_documents method to return zero
    mock_mongo_client.return_value.__getitem__.return_value.__getitem__.return_value.count_documents.return_value = 0
    
    # Test
    assert adapter.entry_exists(collection_name, query) == False
