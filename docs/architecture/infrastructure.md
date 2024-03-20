# Infrastructure Layer

This layer acts as the bridge between the inner circles (use cases and entities) and the outer circles (frameworks, databases, web interfaces)

#### `mongo_client.py`

This setup centralizes your MongoDB configuration and connection logic, making it easier to manage and reuse across different parts of your application.

```python
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

class MongoDBClient:
    def __init__(self, uri, dbname):
        self.uri = uri
        self.dbname = dbname
        self.client = None
        self.db = None

    def connect(self):
        """Connect to MongoDB and select the database."""
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.dbname]
            # Test connection
            self.client.admin.command('ping')
            print("MongoDB connection successful.")
        except ConnectionFailure:
            print("MongoDB connection failed.")
            self.client = None

    def get_database(self):
        """Return the database instance if connected."""
        if self.client and self.db:
            return self.db
        else:
            print("Not connected to MongoDB.")
            return None

    def close(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            print("MongoDB connection closed.")

# Example usage
if __name__ == "__main__":
    uri = "mongodb://localhost:27017/"
    dbname = "your_database_name"
    mongo_client = MongoDBClient(uri, dbname)
    mongo_client.connect()
    db = mongo_client.get_database()
    # Now you can use `db` to interact with your database
    mongo_client.close()

```

- **MongoDBClient class**: A class that encapsulates the logic for connecting to MongoDB, handling connection failures, and providing access to the database.

- **connect method**: Establishes a connection to MongoDB using the provided URI and selects the database. It also performs a simple operation (`ping` command) to verify the connection.

- **get_database method**: Returns the selected database object if connected, which adapters can use to perform database operations.

- **get_database method**: Returns the selected database object if connected, which adapters can use to perform database operations.