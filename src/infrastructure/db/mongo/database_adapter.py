"""
DatabaseAdapter defines a protocol (interface) for database operations, ensuring a clean separation 
between business logic and database implementation. 

By defining this interface, we allow the application to depend on an abstract database contract rather 
than a specific database technology (e.g., MongoDB, PostgreSQL). 

Any concrete database adapter (e.g., MongoDBAdapter) must implement these methods, ensuring that the 
core application logic remains database-agnostic and easily testable.

New developers should implement this interface when integrating a new database or modifying existing storage logic.
"""


from typing import Protocol, Dict, Any

class DatabaseAdapter(Protocol):
    def entry_exists(self, collection_name: str, query: Dict[str, Any]) -> bool:
        pass

    def get_entry_metadata(self, collection_name: str, query: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def update_entry(self, collection_name: str, identifier: str, data: Dict[str, Any]) -> None:
        pass

    def get_raw_documents_from_source(self, collection_name: str, source: str) -> Dict[str, Any]:
        pass
