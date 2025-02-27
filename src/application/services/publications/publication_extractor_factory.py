from src.application.services.publications.publication_extractor import PublicationExtractor
from src.application.services.publications.bioconductor_extractor_extandardizer import BioconductorPublicationExtractor
from src.application.services.publications.biotools_extractor_extandardizer import BiotoolsPublicationExtractor
from src.application.services.publications.toolshed_extractor_extandardizer import ToolshedPublicationExtractor
from src.application.services.publications.opeb_metrics_extractor_extandardizer import OPEBMetricsPublicationExtractor
from src.application.services.publications.bioconda_recipes_extractor_extandardizer import BiocondaRecipesPublicationExtractor

from typing import Dict, Any

class ExtractorFactory:
    """Factory for creating the appropriate publication standardizer."""
    
    _extractors = {
        "bioconductor": BioconductorPublicationExtractor,
        "biotools": BiotoolsPublicationExtractor,
        "toolshed": ToolshedPublicationExtractor,
        "opeb_metrics": OPEBMetricsPublicationExtractor,
        "bioconda_recipes": BiocondaRecipesPublicationExtractor
    }

    @classmethod
    def get_extractor(cls, source: str) -> PublicationExtractor:
        """Returns the appropriate extractor based on the source name."""
        print(source)
        if source not in cls._extractors:
            raise ValueError(f"Unsupported source: {source}")
        return cls._extractors[source]