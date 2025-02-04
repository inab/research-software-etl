from src.core.domain.services.publications.publication_standardizer import PublicationStandardizer
from src.core.domain.services.publications.bioconductor_publication_standardizer import BioconductorPublicationStandardizer
from typing import Dict, Any

class StandardizerFactory:
    """Factory for creating the appropriate publication standardizer."""
    
    standardizers = {
        "bioconductor": BioconductorPublicationStandardizer,
    }

    @staticmethod
    def get_standardizer(source: str, raw_data: Dict[str, Any]) -> PublicationStandardizer:
        """Returns the appropriate standardizer based on the source name."""
        if source not in StandardizerFactory.standardizers:
            raise ValueError(f"Unsupported source: {source}")
        return StandardizerFactory.standardizers[source](raw_data)
