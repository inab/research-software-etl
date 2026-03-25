import os
import pytest
from dotenv import load_dotenv
from infrastructure.db.mongo.mongo_adapter import MongoDBAdapter
from infrastructure.db.database_adapter import DatabaseAdapter
import logging
from sshtunnel import SSHTunnelForwarder
import pymongo

# Load .env variables
load_dotenv(dotenv_path='.env', override=True)
logger = logging.getLogger("rs-etl-pipeline")

'''
@pytest.mark.manual
def test_mongo_debug_constructor():
    from infrastructure.db.mongo.mongo_adapter import MongoDBAdapter
    print("MongoDBAdapter class is:", MongoDBAdapter)

    MongoDBAdapter._client = None

    print("Before creating adapter")
    """Initialize MongoDB Client (optionally via SSH tunnel)"""

    logger.info("Initializing MongoDB client")
    use_ssh_tunnel = os.getenv('USE_SSH_TUNNEL', 'false').lower() == 'true'
    mongo_host = os.getenv('MONGO_HOST', 'localhost')
    mongo_port = int(os.getenv('MONGO_PORT', '27017'))
    mongo_user = os.getenv('MONGO_USER')
    mongo_pass = os.getenv('MONGO_PWD')
    mongo_auth_src = os.getenv('MONGO_AUTH_SRC', 'admin')

    print(f"USE_SSH_TUNNEL is {use_ssh_tunnel}")
    if use_ssh_tunnel:
        print("Using SSH tunnel to connect to MongoDB")

        ssh_host = os.getenv('SSH_HOST')
        ssh_port = int(os.getenv('SSH_PORT', '22'))
        ssh_user = os.getenv('SSH_USER')
        ssh_key = os.getenv('SSH_KEY')  # Or use SSH_PASSWORD

        if not all([ssh_host, ssh_user, ssh_key]):
            raise ValueError("Missing SSH connection details (SSH_HOST, SSH_USER, SSH_KEY)")

        tunnel = SSHTunnelForwarder(
            (ssh_host, ssh_port),
            ssh_username=ssh_user,
            ssh_private_key=ssh_key,
            remote_bind_address=(mongo_host, mongo_port),
            local_bind_address=('127.0.0.1', 0)  # Let OS pick an available port
        )
        tunnel.start()
        MongoDBAdapter._tunnel = tunnel  # Keep reference to prevent garbage collection
        local_port = tunnel.local_bind_port
        print(f"SSH tunnel established on local port {local_port}")

        mongo_uri = f'mongodb://127.0.0.1:{local_port}/'
    else:
        logger.info(f"Connecting directly to MongoDB at {mongo_host}:{mongo_port}")
        mongo_uri = f'mongodb://{mongo_host}:{mongo_port}/'

    try:
        if mongo_user and mongo_pass:
            client = pymongo.MongoClient(
                mongo_uri,
                username=mongo_user,
                password=mongo_pass,
                authSource=mongo_auth_src,
                authMechanism='SCRAM-SHA-256',
                maxPoolSize=100,
                serverSelectionTimeoutMS=5000
            )
        else:
            logger.debug("No MongoDB credentials provided. Connecting without authentication.")
            client = pymongo.MongoClient(
                mongo_uri,
                maxPoolSize=100,
                serverSelectionTimeoutMS=5000
            )

        client.admin.command('ping')
        logger.info("MongoDB connection established successfully")

    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        if MongoDBAdapter._tunnel:
            MongoDBAdapter._tunnel.stop()
        raise

    db = client[os.getenv('MONGO_DB', 'oeb-research-software')]
    collections = db.list_collection_names()
    print(collections)
    assert isinstance(collections, list), "Expected a list of collections"
    print("Connected! Collections:", collections)

'''



@pytest.mark.manual
def test_mongodb_connection_through_ssh():
    """
    Manual test to verify MongoDB connection via SSH tunnel using MongoDBAdapter.
    Requires:
    - Valid .env file with SSH and MongoDB config
    """

    required_vars = ['USE_SSH_TUNNEL', 'SSH_HOST', 'SSH_USER', 'SSH_KEY', 'MONGO_HOST', 'MONGO_PORT', 'MONGO_USER', 'MONGO_PWD', 'MONGO_AUTH_SRC', 'MONGO_DB']
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        pytest.skip(f"Missing required env vars: {', '.join(missing)}")

    for var in required_vars:
        print(f"{var}: {os.getenv(var)}")

    print("Testing MongoDB connection through SSH tunnel...")
    MongoDBAdapter._client = None
    adapter = MongoDBAdapter()
    collections = adapter.db.list_collection_names()
    assert isinstance(collections, list), "Expected a list of collections"
    print("Connected! Collections:", collections)
