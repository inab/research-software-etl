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
