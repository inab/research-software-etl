import pytest
from unittest.mock import patch

from infrastructure.db.mongo.mongo_adapter import MongoDBAdapter


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


@pytest.fixture
def mock_mongo_client():
    """
    Patch pymongo.MongoClient and clear the class-level client cache.

    MongoDBAdapter._client is shared across every instance, so without resetting
    it a client built by an earlier test (or an earlier import) would be reused
    and the mock would never be called.
    """
    MongoDBAdapter._client = None
    with patch('pymongo.MongoClient') as mock_client:
        yield mock_client
    MongoDBAdapter._client = None


def test_mongodb_adapter_connects_lazily(mock_env_vars, mock_mongo_client):
    """Constructing the adapter must not open a connection."""
    MongoDBAdapter()
    mock_mongo_client.assert_not_called()


def test_mongodb_adapter_init(mock_env_vars, mock_mongo_client):
    adapter = MongoDBAdapter()

    # The connection is made on first use, not at construction.
    _ = adapter.client

    mock_mongo_client.assert_called_once_with(
        'mongodb://localhost:27017',
        username='user',
        password='password',
        authSource='admin',
        authMechanism='SCRAM-SHA-256',
        maxPoolSize=100,
        serverSelectionTimeoutMS=5000,
    )


def _set_count(mock_client, count):
    collection = mock_client.return_value.__getitem__.return_value.__getitem__.return_value
    collection.count_documents.return_value = count


def test_entry_exists_true(mock_env_vars, mock_mongo_client):
    adapter = MongoDBAdapter()
    _set_count(mock_mongo_client, 1)

    assert adapter.entry_exists('test_collection', 'some_id') is True


def test_entry_exists_false(mock_env_vars, mock_mongo_client):
    adapter = MongoDBAdapter()
    _set_count(mock_mongo_client, 0)

    assert adapter.entry_exists('test_collection', 'nonexistent_id') is False


def test_entry_exists_queries_by_id(mock_env_vars, mock_mongo_client):
    adapter = MongoDBAdapter()
    _set_count(mock_mongo_client, 1)

    adapter.entry_exists('test_collection', 'some_id')

    collection = mock_mongo_client.return_value.__getitem__.return_value.__getitem__.return_value
    collection.count_documents.assert_called_once_with({'_id': 'some_id'})
