
from core.domain.services.transformation.metadata_standardizer import MetadataStandardizer
from unittest.mock import patch


class Standardizer(MetadataStandardizer):
    '''
    MetadataStandardizer subclass with dummy transform_one method for testing purposes.
    '''

    def __init__(self, source='source', ignore_empty_bioconda_types=False):
        MetadataStandardizer.__init__(self, source, ignore_empty_bioconda_types)

    def transform_one(self, tool, standardized_tools):
        return standardized_tools

class TestGenerateBiocondaTypes:

    # Returns a dictionary with the types of the bioconda tools in the pretools collection.
    def test_returns_dictionary_with_types(self):
        # Initialize the class object
        generator = Standardizer()
        result = generator.generate_bioconda_types()
    
        # Assert the result is a dictionary with the correct types
        assert isinstance(result, dict)
        assert len(result) > 0
        
        random_key = list(result.keys())[0]
        assert isinstance(random_key, str)
        assert isinstance(result[random_key], str)

    # Returns an empty dictionary when there are no bioconda tools in the pretools collection or the collection is empty.
    
    # This patch must contain the target as called by the function generate_bioconda_types()
    @patch('src.core.shared.utils.connect_collection')
    def test_returns_empty_dictionary(self, mock_connect_collection):
        # Initialize the class object
        generator = Standardizer()
    
        # Mock the connect_collection method
        mock_connect_collection.return_value = {}
            
        # Invoke the generate_bioconda_types method
        result = generator.generate_bioconda_types()
    
        # Assert the result is an empty dictionary
        assert isinstance(result, dict)
        assert len(result) == 0

    # Handles cases where the pretools collection is not accessible.
    @patch('src.core.shared.utils.connect_collection')
    def test_handles_inaccessible_pretools_collection(self, mock_connect_collection):
        # Initialize the class object
        generator = Standardizer()
    
        # Mock the connect_collection method
        def side_effect(args):
            raise Exception('Unable to connect to pretools collection')
        
        mock_connect_collection.return_value = side_effect

        result = generator.generate_bioconda_types()
    
        # Assert the result is an empty dictionary
        assert isinstance(result, dict)
        assert len(result) == 0

   
   
