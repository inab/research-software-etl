from abc import ABC, abstractmethod

class URLResolver(ABC):
    @abstractmethod
    def resolve(self, url: str) -> bool:
        """Checks if a URL is reachable."""
        pass