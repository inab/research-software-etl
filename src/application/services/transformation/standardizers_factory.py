from src.application.services.transformation.bioconda_opeb import biocondaOPEBStandardizer
from src.application.services.transformation.bioconda_recipes import biocondaRecipesStandardizer
from src.application.services.transformation.bioconductor import bioconductorStandardizer
from src.application.services.transformation.biotools_opeb import biotoolsOPEBStandardizer
from src.application.services.transformation.galaxy_config import toolshedStandardizer
from src.application.services.transformation.galaxy_metadata import galaxyMetadataStandardizer
from src.application.services.transformation.galaxy_opeb import galaxyOPEBStandardizer
from src.application.services.transformation.opeb_metrics import OPEBMetricsStandardizer
from src.application.services.transformation.source_forge import sourceforgeStandardizer
from src.application.services.transformation.github import githubStandardizer


class MetadataStandardizerFactory:
    _standardizers = {}

    @classmethod
    def register_standardizer(cls, source, standardizer_cls):
        cls._standardizers[source] = standardizer_cls

    @classmethod
    def get_standardizer(cls, source):
        standardizer_cls = cls._standardizers.get(source)
        if not standardizer_cls:
            raise ValueError("No standardizer available for source {}".format(source))
        return standardizer_cls()

# Register all available 
MetadataStandardizerFactory.register_standardizer('bioconda', biocondaOPEBStandardizer)
MetadataStandardizerFactory.register_standardizer('bioconda_recipes', biocondaRecipesStandardizer)
MetadataStandardizerFactory.register_standardizer('bioconductor', bioconductorStandardizer)
MetadataStandardizerFactory.register_standardizer('biotools', biotoolsOPEBStandardizer)
MetadataStandardizerFactory.register_standardizer('toolshed', toolshedStandardizer)
MetadataStandardizerFactory.register_standardizer('galaxy_metadata', galaxyMetadataStandardizer)
MetadataStandardizerFactory.register_standardizer('galaxy', galaxyOPEBStandardizer)
MetadataStandardizerFactory.register_standardizer('opeb_metrics', OPEBMetricsStandardizer)
MetadataStandardizerFactory.register_standardizer('sourceforge', sourceforgeStandardizer)
MetadataStandardizerFactory.register_standardizer('github', githubStandardizer)



