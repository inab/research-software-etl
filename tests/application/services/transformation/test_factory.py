import pytest
from src.application.services.transformation.standardizers_factory import MetadataStandardizerFactory
from src.application.services.transformation.bioconda_opeb import biocondaOPEBStandardizer
from src.application.services.transformation.bioconda_recipes import biocondaRecipesStandardizer
from src.application.services.transformation.bioconductor import bioconductorStandardizer
from src.application.services.transformation.biotools_opeb import biotoolsOPEBStandardizer
from src.application.services.transformation.galaxy_config import toolshedStandardizer
from src.application.services.transformation.galaxy_metadata import galaxyMetadataStandardizer
from src.application.services.transformation.galaxy_opeb import galaxyOPEBStandardizer
from src.application.services.transformation.opeb_metrics import OPEBMetricsStandardizer
from src.application.services.transformation.source_forge import sourceforgeStandardizer

standardizer_tests = [
    ('bioconda', biocondaOPEBStandardizer),
    ('bioconda_recipes', biocondaRecipesStandardizer),
    ('bioconductor', bioconductorStandardizer),
    ('biotools', biotoolsOPEBStandardizer),
    ('toolshed', toolshedStandardizer),
    ('galaxy_metadata', galaxyMetadataStandardizer),
    ('galaxy', galaxyOPEBStandardizer),
    ('opeb_metrics', OPEBMetricsStandardizer),
    ('sourceforge', sourceforgeStandardizer),
]

@pytest.mark.parametrize("source,expected_class", standardizer_tests )
def test_factory_returns_correct_standardizer(source, expected_class):
    """
    Tests that the factory returns the correct standardizer instance for given source identifiers.
    """
    standardizer = MetadataStandardizerFactory.get_standardizer(source)
    assert isinstance(standardizer, expected_class), f"Factory should create an instance of {expected_class.__name__} for source '{source}'"

def test_factory_raises_error_for_invalid_source():
    """
    Tests that the factory raises a ValueError for unknown source identifiers.
    """
    with pytest.raises(ValueError) as excinfo:
        MetadataStandardizerFactory.get_standardizer('UnknownSource')
    assert "No standardizer available for source UnknownSource" in str(excinfo.value), "Expected ValueError for unknown sources"
