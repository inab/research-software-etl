from src.application.services.publications.publication_standardizer import PublicationStandardizer
from src.application.services.publications.bioconductor_extractor_extandardizer import BioconductorPublicationStandardizer
from src.application.services.publications.biotools_extractor_extandardizer import BiotoolsPublicationStandardizer
from src.application.services.publications.toolshed_extractor_extandardizer import ToolshedPublicationStandardizer

from typing import Dict, Any

class StandardizerFactory:
    """Factory for creating the appropriate publication standardizer."""
    
    _standardizers = {
        "bioconductor": BioconductorPublicationStandardizer,
        "biotools": BiotoolsPublicationStandardizer,
        "toolshed": ToolshedPublicationStandardizer
    }

    @classmethod
    def get_standardizer(cls, source: str) -> PublicationStandardizer:
        """Returns the appropriate standardizer based on the source name."""
        if source not in cls._standardizers:
            raise ValueError(f"Unsupported source: {source}")
        return cls._standardizers[source]
