from FAIRsoft.classes.documentation import documentation_item
from pydantic import HttpUrl, ValidationError
import pytest

#------------------------------------------------------------
# Test Class documentation_item
#------------------------------------------------------------

class TestDocumentationItem:

    # Creating a new instance of documentation_item with valid url and type.
    def test_valid_url_and_type(self):
        url = "https://example.com"
        doc_item = documentation_item(url=url, type="general")
        assert doc_item.url == HttpUrl(url)
        assert doc_item.type == "general"

    # Creating a new instance of documentation_item with valid url and default type.
    def test_valid_url_and_default_type(self):
        url = "https://example.com"
        doc_item = documentation_item(url=url)
        assert doc_item.url == HttpUrl(url)
        assert doc_item.type == "general"

    # Validating a dictionary with valid 'type' and 'url' fields to create a documentation_item instance.
    def test_valid_dictionary(self):
        data = {"type": "general", "url": "https://example.com"}
        doc_item = documentation_item(**data)
        assert doc_item.url == HttpUrl(data["url"])
        assert doc_item.type == data["type"]

    # Creating a new instance of documentation_item with an invalid url.
    def test_invalid_url(self):
        url = "invalid_url"
        with pytest.raises(ValueError):
            doc_item = documentation_item(url=url, type="general")

    # Creating a new instance of documentation_item with an invalid type.
    def test_invalid_type(self):
        url = "https://example.com"
        type = 123
        with pytest.raises(ValidationError):
            doc_item = documentation_item(url=url, type=type)

    # Creating a new instance of documentation_item with both invalid url and type.
    def test_invalid_url_and_type(self):
        url = "invalid_url"
        type = 123
        with pytest.raises(ValueError):
            doc_item = documentation_item(url=url, type=type)

#------------------------------------------------------------
# Test Validators
#------------------------------------------------------------

class TestIfSimpleDocs:

    # Transforms a list with two strings into a dictionary with 'type' and 'url' keys.
    def test_transform_list_to_dict(self):
        # Arrange
        data = ['type', 'url']
        expected_result = {'type': 'type', 'url': 'url'}
    
        # Act
        result = documentation_item.if_simple_docs(data)
    
        # Assert
        assert result == expected_result

    # Returns a dictionary unmodified if it does not meet the criteria for transformation.
    def test_return_unmodified_dict(self):
        # Arrange
        data = {'key': 'value'}
    
        # Act
        result = documentation_item.if_simple_docs(data)
    
        # Assert
        assert result == data

    # Returns data if input is not a list or dictionary.
    def test_return_none_for_invalid_input(self):
        # Arrange
        data = 123
    
        # Act
        result = documentation_item.if_simple_docs(data)
    
        # Assert
        assert result is data

    # Returns None if input list does not have exactly two elements.
    def test_return_none_for_list_with_incorrect_length(self):
        # Arrange
        data = ['type']
    
        # Act
        result = documentation_item.if_simple_docs(data)
    
        # Assert
        assert result is data

    # Returns None if input list elements are not both strings.
    def test_return_none_for_list_with_non_string_elements(self):
        # Arrange
        data = [1, 2]
    
        # Act
        result = documentation_item.if_simple_docs(data)
    
        # Assert
        assert result is data

    # Returns input dictionary unmodified if it does not have 'type' and 'url' keys.
    def test_return_unmodified_dict_if_missing_keys(self):
        # Arrange
        data = {'key': 'value'}
    
        # Act
        result = documentation_item.if_simple_docs(data)
    
        # Assert
        assert result == data

class TestReplaceDocumentationType:

    # Replaces 'documentation' with 'general' when 'type' is present and equal to 'documentation'.
    def test_replace_documentation_type_replaces_type_when_type_is_documentation(self):
        # Arrange
        data = {'type': 'documentation'}
    
        # Act
        result = documentation_item.replace_documentation_type(data)
    
        # Assert
        assert result == {'type': 'general'}

    # Returns the input data unmodified when 'type' is not present in the input data.
    def test_replace_documentation_type_returns_input_data_unmodified_when_type_not_present(self):
        # Arrange
        data = {'url': 'https://example.com'}
    
        # Act
        result = documentation_item.replace_documentation_type(data)
    
        # Assert
        assert result == {'url': 'https://example.com'}

    # Returns the input data unmodified when 'type' is present but not equal to 'documentation'.
    def test_replace_documentation_type_returns_input_data_unmodified_when_type_not_equal_to_documentation(self):
        # Arrange
        data = {'type': 'other', 'url': 'https://example.com'}
    
        # Act
        result = documentation_item.replace_documentation_type(data)
    
        # Assert
        assert result == {'type': 'other', 'url': 'https://example.com'}

    # Returns the input data unmodified when the input data is an empty dictionary.
    def test_replace_documentation_type_returns_input_data_unmodified_when_input_data_is_empty_dictionary(self):
        # Arrange
        data = {}
    
        # Act
        result = documentation_item.replace_documentation_type(data)
    
        # Assert
        assert result == {}

    # Returns the input data unmodified when the input data is None.
    def test_replace_documentation_type_returns_input_data_unmodified_when_input_data_is_none(self):
        # Arrange
        data = None
    
        # Act
        result = documentation_item.replace_documentation_type(data)
    
        # Assert
        assert result is None

    # Returns the input data unmodified when the input data is not a dictionary.
    def test_replace_documentation_type_returns_input_data_unmodified_when_input_data_is_not_dictionary(self):
        # Arrange
        data = 'not a dictionary'
    
        # Act
        result = documentation_item.replace_documentation_type(data)
    
        # Assert
        assert result == 'not a dictionary'