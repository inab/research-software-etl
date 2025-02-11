from abc import ABC, abstractmethod
from typing import Dict, Any

class PublicationExtractor(ABC):
    """Abstract base class for all publication extractors."""
    @abstractmethod
    @classmethod
    def extract_publications(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts publication data from the raw source data."""
        pass

