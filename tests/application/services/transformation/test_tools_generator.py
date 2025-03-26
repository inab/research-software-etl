
from src.application.services.transformation.metadata_standardizers import MetadataStandardizer
from unittest.mock import patch


class Standardizer(MetadataStandardizer):
    '''
    MetadataStandardizer subclass with dummy transform_one method for testing purposes.
    '''

    def __init__(self, source='source', ignore_empty_bioconda_types=False):
        MetadataStandardizer.__init__(self, source, ignore_empty_bioconda_types)

    def transform_one(self, tool, standardized_tools):
        return standardized_tools

