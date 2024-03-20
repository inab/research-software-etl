
from FAIRsoft.transformation.utils import toolGenerator
from unittest.mock import patch

class TestGenerateBiocondaTypes:

    # Returns a dictionary with the types of the bioconda tools in the pretools collection.
    def test_returns_dictionary_with_types(self):
        # Initialize the class object
        generator = toolGenerator([], 'source')
        result = generator.generate_bioconda_types()
    
        # Assert the result is a dictionary with the correct types
        assert isinstance(result, dict)
        assert len(result) > 0
        
        random_key = list(result.keys())[0]
        assert isinstance(random_key, str)
        assert isinstance(result[random_key], str)

    # Returns an empty dictionary when there are no bioconda tools in the pretools collection or the collection is empty.
        
    @patch('FAIRsoft.transformation.utils.connect_collection')
    def test_returns_empty_dictionary(self, mock_connect_collection):
        # Initialize the class object
        generator = toolGenerator([], 'source')
    
        # Mock the connect_collection method
        mock_connect_collection.return_value = {}
            
        # Invoke the generate_bioconda_types method
        result = generator.generate_bioconda_types()
    
        # Assert the result is an empty dictionary
        assert isinstance(result, dict)
        assert len(result) == 0

    # Handles cases where the pretools collection is not accessible.
    @patch('FAIRsoft.transformation.utils.connect_collection')
    def test_handles_inaccessible_pretools_collection(self, mock_connect_collection):
        # Initialize the class object
        generator = toolGenerator([], 'source')
    
        # Mock the connect_collection method
        def side_effect(args):
            raise Exception('Unable to connect to pretools collection')
        
        mock_connect_collection.return_value = side_effect

        result = generator.generate_bioconda_types()
    
        # Assert the result is an empty dictionary
        assert isinstance(result, dict)
        assert len(result) == 0

   
   
