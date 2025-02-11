from abc import ABC, abstractmethod
from typing import Dict, Any

class PublicationExtractor(ABC):
    """Abstract base class for all publication extractors."""

    def __init__(self, raw_data: Dict[str, Any]):
        self.raw_data = raw_data  # Store raw source data

    @abstractmethod
    def extract_publications(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts publication data from the raw source data."""
        pass

