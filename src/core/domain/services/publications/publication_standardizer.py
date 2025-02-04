from abc import ABC, abstractmethod
from typing import Dict, Any
from datetime import datetime

class PublicationStandardizer(ABC):
    """Abstract base class for all publication standardizers."""

    def __init__(self, raw_data: Dict[str, Any]):
        self.raw_data = raw_data  # Store raw source data

    @abstractmethod
    def standardize(self) -> Dict[str, Any]:
        """Transforms raw publication data into a standardized format."""
        pass

 