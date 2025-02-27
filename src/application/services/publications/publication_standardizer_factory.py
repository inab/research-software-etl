from src.application.services.publications.publication_standardizer import PublicationStandardizer
from src.application.services.publications.bioconductor_extractor_standardizer import BioconductorPublicationStandardizer
from src.application.services.publications.biotools_extractor_standardizer import BiotoolsPublicationStandardizer
from src.application.services.publications.toolshed_extractor_standardizer import ToolshedPublicationStandardizer
from src.application.services.publications.opeb_metrics_extractor_standardizer import OPEBMetricsPublicationStandardizer
from src.application.services.publications.bioconda_recipes_extractor_standardizer import BiocondaRecipesPublicationStandardizer


class StandardizerFactory:
    """Factory for creating the appropriate publication standardizer."""
    
    _standardizers = {
        "bioconductor": BioconductorPublicationStandardizer,
        "biotools": BiotoolsPublicationStandardizer,
        "toolshed": ToolshedPublicationStandardizer,
        "opeb_metrics": OPEBMetricsPublicationStandardizer,
        "bioconda_recipes": BiocondaRecipesPublicationStandardizer
    }

    @classmethod
    def get_standardizer(cls, source: str) -> PublicationStandardizer:
        """Returns the appropriate standardizer based on the source name."""
        if source not in cls._standardizers:
            raise ValueError(f"Unsupported source: {source}")
        return cls._standardizers[source]
