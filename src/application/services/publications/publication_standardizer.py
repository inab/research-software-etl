from abc import ABC, abstractmethod
from typing import Dict, Any

class PublicationStandardizer(ABC):
    """Abstract base class for all publication standardizers."""

    @abstractmethod
    @classmethod
    def standardize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transforms raw publication data into a standardized format."""
        pass

 