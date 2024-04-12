from src.core.use_cases.data_transformation.main import transform_this_source, get_raw_data_db
from src.core.domain.entities.software_instance.main import software_types
import src.core.shared.utils
import pytest

class TestTransformThisSource:

    # Transforms raw data from one specific source into instances
    def test_transform_raw_data(self):
        # Arrange
        raw_data = [
            {
                'data' : {
                    '@id': 'https://openebench.bsc.es/monitor/tool/biotools:tool-1/cmd/www.bio-mol.unisi.it',
                    '_id': 'https://openebench.bsc.es/monitor/tool/biotools:tool-1/cmd/www.bio-mol.unisi.it', 
                    '@label': 'Tool 1', 
                    '@version': '1.0', 
                    '@type': 'cmd',
                    'name': 'Tool 1'
                }
            }, 
            {   
                'data' : {
                    '@id': 'https://openebench.bsc.es/monitor/tool/biotools:tool-2/lib/www.bio-mol.unisi.it',
                    '_id': 'https://openebench.bsc.es/monitor/tool/biotools:tool-1/cmd/www.bio-mol.unisi.it', 
                    '@label': 'Tool 2', 
                    '@version': '2.0', 
                    '@type': 'lib',
                    'name': 'Tool 2'
                }
            }, 
            {   
                'data' : {
                    '@id': 'https://openebench.bsc.es/monitor/tool/biotools:tool-3/lib/www.bio-mol.unisi.it',
                    '_id': 'https://openebench.bsc.es/monitor/tool/biotools:tool-1/cmd/www.bio-mol.unisi.it', 
                    '@label': 'Tool 3', 
                    '@version': '2.0', 
                    '@type': 'lib',
                    'name': 'Tool 3'
                }
            }
            ]
        this_source_label = 'biotools'
    
        # Act
        result = transform_this_source(raw_data, this_source_label)
    
        # Assert
        assert len(result) == 3
        assert result[0]['name'] == 'tool 1'
        assert result[0]['version'] == ['1.0']
        assert result[0]['type'] == software_types.cmd
        assert result[0]['description'] == []
        assert result[0]['publication'] == []
        
        assert result[1]['name'] == 'tool 2'
        assert result[1]['version'] == ['2.0']
        assert result[1]['type'] == software_types.lib
        assert result[0]['description'] == []
        assert result[0]['publication'] == []

    # Empty raw data returns an empty list
    def test_empty_raw_data(self):
        # Arrange
        raw_data = []
        this_source_label = 'biotools'
    
        # Act
        result = transform_this_source(raw_data, this_source_label)
    
        # Assert
        assert isinstance(result, list)
        assert len(result) == 0

    # Invalid raw data raises an exception
    def test_invalid_raw_data(self):
        # Arrange
        raw_data = None
        this_source_label = 'biotools'
    
        # Act and Assert
        with pytest.raises(Exception):
            transform_this_source(raw_data, this_source_label)

    # Invalid source label raises an exception
    def test_invalid_source_label(self):
        # Arrange
        raw_data = [{'name': 'Tool 1', 'version': '1.0'}, {'name': 'Tool 2', 'version': '2.0'}]
        this_source_label = 'invalid_label'
    
        # Act and Assert
        with pytest.raises(Exception):
            transform_this_source(raw_data, this_source_label)



class TestGetRawDataDb:

    # Returns a list of dictionaries when given a valid source label.
    def test_valid_source_label(self, mocker):
        # Mock the connect_collection function
        mocker.patch('src.core.shared.utils.connect_collection')
        alambique_mock = mocker.MagicMock()
        src.core.shared.utils.connect_collection.return_value = alambique_mock

        # Mock the find function
        alambique_mock.find.return_value = [{'key1': 'value1'}, {'key2': 'value2'}]

        # Invoke the function under test
        result = get_raw_data_db('BIOCONDUCTOR')

        # Assert the result
        assert result == [{'key1': 'value1'}, {'key2': 'value2'}]

    # Returns an empty list when given a source label that does not exist in the database.
    def test_invalid_source_label(self, mocker):
        # Mock the connect_collection function
        mocker.patch('src.core.shared.utils.connect_collection')
        alambique_mock = mocker.MagicMock()
        src.core.shared.utils.connect_collection.return_value = alambique_mock

        # Mock the find function
        alambique_mock.find.return_value = []

        # Invoke the function under test
        result = get_raw_data_db('INVALID_SOURCE')

        # Assert the result
        assert result == []

    # Returns a list of dictionaries with expected keys and values when given a valid source label.
    def test_valid_source_label_with_expected_data(self, mocker):
        # Mock the connect_collection function
        mocker.patch('src.core.shared.utils.connect_collection')
        alambique_mock = mocker.MagicMock()
        src.core.shared.utils.connect_collection.return_value = alambique_mock

        # Mock the find function
        alambique_mock.find.return_value = [{'key1': 'value1', 'key2': 'value2'}]

        # Invoke the function under test
        result = get_raw_data_db('BIOCONDUCTOR')

        # Assert the result
        assert result == [{'key1': 'value1', 'key2': 'value2'}]

    # Returns an empty list when the database is empty.
    def test_empty_database(self, mocker):
        # Mock the connect_collection function
        mocker.patch('src.core.shared.utils.connect_collection')
        alambique_mock = mocker.MagicMock()
        src.core.shared.utils.connect_collection.return_value = alambique_mock

        # Mock the find function
        alambique_mock.find.return_value = []

        # Invoke the function under test
        result = get_raw_data_db('BIOCONDUCTOR')

        # Assert the result
        assert result == []

    # Raises an exception when the database connection fails.
    def test_database_connection_failure(self, mocker):
        # Mock the connect_collection function to raise an exception
        mocker.patch('src.core.shared.utils.connect_collection', side_effect=Exception('Database connection failed'))

        # Invoke the function under test and assert that it raises an exception
        with pytest.raises(Exception):
            get_raw_data_db('BIOCONDUCTOR')

    # Returns a list of dictionaries with expected keys and empty values when given a valid source label and the corresponding data in the database has missing values.
    def test_valid_source_label_with_missing_values(self, mocker):
        # Mock the connect_collection function
        mocker.patch('src.core.shared.utils.connect_collection')
        alambique_mock = mocker.MagicMock()
        src.core.shared.utils.connect_collection.return_value = alambique_mock

        # Mock the find function
        alambique_mock.find.return_value = [{'key1': None, 'key2': None}]

        # Invoke the function under test
        result = get_raw_data_db('BIOCONDUCTOR')

        # Assert the result
        assert result == [{'key1': None, 'key2': None}]