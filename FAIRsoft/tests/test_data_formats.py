
from FAIRsoft.classes.data_format import data_format, free_text_data_format,  data_type
from pydantic import HttpUrl, ValidationError

import pytest

### ---------------------------------------------------------------------- ###
### Formats classes
### ---------------------------------------------------------------------- ###

### ------- Data Format class ------- ###
            
class TestDataFormat:

    # The class can be instantiated with valid arguments for all attributes.
    def test_instantiation_with_valid_arguments_all_attributes(self):
        # Arrange
        vocabulary = "EDAM"
        term = "Sequence format"
        uri = "http://edamontology.org/format_1929"
        datatype = {
            "vocabulary": "EDAM",
            "term": "Sequence",
            "uri": "http://edamontology.org/data_0006"
        }
    
        # Act
        instance = data_format(vocabulary=vocabulary, term=term, uri=uri, datatype=datatype)
    
        # Assert
        assert isinstance(instance, data_format)
        assert instance.vocabulary == vocabulary
        assert instance.term == term
        assert instance.uri == HttpUrl(uri)
        assert instance.datatype == data_type(**datatype)

    # The class can be instantiated with valid arguments for some attributes.
    def test_instantiation_with_valid_arguments_some_attributes(self):
        # Arrange
        vocabulary = "EDAM"
        term = "Sequence format"
    
        # Act
        instance = data_format(vocabulary=vocabulary, term=term)
    
        # Assert
        assert isinstance(instance, data_format)
        assert instance.vocabulary == vocabulary
        assert instance.term == term
        assert instance.uri is None
        assert instance.datatype is None

    # The class CANNOT be instantiated with invalid arguments for all attributes.
    def test_instantiation_with_invalid_arguments_all_attributes(self):
        # Arrange
        vocabulary = 123
        term = 456
        uri = "http://edamontology.org/format_1929"
        datatype = {
            "vocabulary": "EDAM",
            "term": "Sequence",
            "uri": "http://edamontology.org/data_0006"
        }
    
        # Act and Assert
        with pytest.raises(ValidationError):
            instance = data_format(vocabulary=vocabulary, term=term, uri=uri, datatype=datatype)

    # The class CANNOT be instantiated with invalid arguments for some attributes.
    def test_instantiation_with_invalid_arguments_some_attributes(self):
        # Arrange
        vocabulary = "EDAM"
        term = 456
    
        # Act and Assert
        with pytest.raises(ValidationError):
            instance = data_format(vocabulary=vocabulary, term=term)

    # The class CANNOT be instantiated with invalid arguments for only one attribute.
    def test_instantiation_with_invalid_arguments_one_attribute(self):
        # Arrange
        vocabulary = "EDAM"
        term = "Sequence format"
        uri = 123
        datatype = {
            "vocabulary": "EDAM",
            "term": "Sequence",
            "uri": "http://edamontology.org/data_0006"
        }
    
        # Act and Assert
        with pytest.raises(ValidationError):
            instance = data_format(vocabulary=vocabulary, term=term, uri=uri, datatype=datatype)

### ------------------ Free Text Format class ------------------ ###
class TestFreeFormat:

    # Valid term and uri values should succeed.
    def test_valid_term(self):
        input_data = {
            "term": "txt",
            "uri": None
        }
        obj = free_text_data_format(**input_data)
        assert obj.term == "txt"
        assert obj.uri == None

    def test_valid_term_and_uri(self):
        term = "example"
        uri = "http://example.com"
        obj = free_text_data_format(term=term, uri=uri)
        assert obj.term == term
        assert obj.uri == HttpUrl(uri)

    # Valid term and no uri value should succeed.
    def test_valid_term_no_uri(self):
        term = "example"
        obj = free_text_data_format(term=term, uri=None)
        assert obj.term == term
        assert obj.uri is None

    # Valid uri and no term value should succeed.
    def test_valid_uri_no_term(self):
        uri = "http://example.com"
        obj = free_text_data_format(uri=uri)
        assert obj.term == ''
        assert obj.uri == HttpUrl(uri)

    # Empty term and no uri value should succeed.
    def test_empty_term_no_uri(self):
        obj = free_text_data_format(term='')
        assert obj.term == ''
        assert obj.uri is None

    # Invalid uri value should raise a validation error.
    def test_invalid_uri(self):
        term = "example"
        uri = "invalid_uri"
        with pytest.raises(ValueError):
            free_text_data_format(term=term, uri=uri)

    # Invalid term value and a valid uri value should raise a validation error.
    def test_invalid_term(self):
        term = 123
        uri = "http://example.com"
        with pytest.raises(ValueError):
            free_text_data_format(term=term, uri=uri)



### ---------------------------------------------------------------------- ###
### Reformating functions
### ---------------------------------------------------------------------- ###
            
### ------------------ Normalization of Text Data formats ------------------ ###

class TestNormalizeTextFormats:

    # Returns the input term if it is not in the equivalencies list.
    def test_returns_input_term_if_not_in_equivalencies_list(self):
        term = "unknown"
        expected = "unknown"
        result = data_format.normalize_text_formats(term)
        assert result == expected

    # Returns the first element of the equivalencies list if the input term is in the list.
    def test_returns_first_element_of_equivalencies_list_if_input_term_in_list(self):
        term = "TXT"
        expected = "Textual format"
        result = data_format.normalize_text_formats(term)
        assert result == expected

    # Returns the first element of the equivalencies list if the input term is in the list, regardless of case.
    def test_returns_first_element_of_equivalencies_list_if_input_term_in_list_regardless_of_case(self):
        term = "txt"
        expected = "Textual format"
        result = data_format.normalize_text_formats(term)
        assert result == expected

    # Returns an empty string if the input term is an empty string.
    def test_returns_empty_string_if_input_term_is_empty_string(self):
        term = ""
        expected = ""
        result = data_format.normalize_text_formats(term)
        assert result == expected

    # Returns None if the input term is None.
    def test_returns_none_if_input_term_is_none(self):
        term = None
        expected = ''
        result = data_format.normalize_text_formats(term)
        assert result == expected

    # Returns the first element of the equivalencies list if the input term is a single space.
    def test_returns_first_element_of_equivalencies_list_if_input_term_is_single_space(self):
        term = " "
        expected = ""
        result = data_format.normalize_text_formats(term)
        assert result == expected
    

### ------------------ Reformating Free Text Data formats ------------------ ###

class TestReformatFreeTextItems:

    # Should return a dictionary with the normalized format, vocabulary, term and uri when given a valid input
    def test_valid_input(self):
        #reformatted_format = data_format(**input_format)
        reformatted_format = data_format(term = 'txt', uri = None)
        # Assert that the reformatted format has the correct values
        assert reformatted_format.vocabulary == 'EDAM'
        assert reformatted_format.term == 'Textual format'
        assert reformatted_format.uri == HttpUrl('http://edamontology.org/format_2330')
        assert reformatted_format.datatype is None

    # Should return a validation error when given a free text format that does not have a perfect match in EDAMDict
    def test_no_perfect_match(self):
        # Create a dictionary representing the input format
        input_format = {
            "term": "invalid_format",
            "uri": None
        }

        # Assert that a ValidationError is raised        
        with pytest.raises(ValueError):
            reformatted_format = data_format(**input_format)

    # Should return raise a ValueError when given an empty input
    def test_empty_input(self):
        with pytest.raises(ValueError):
            obj = data_format(**{})

    # Should raise a ValueError when given an input that cannot be parsed as a free text data format
    def test_value_error(self):

        with pytest.raises(ValueError):
            obj = data_format(invalid_key="txt")
        

    # Should raise an error when given a dictionary with a format that has an empty term
    def test_empty_term(self):

        with pytest.raises(ValueError):
            obj = data_format(**{  'term': '' })


    # Should raise an error when given a dictionary with a format that has a non-string term
    def test_non_string_term(self):
        with pytest.raises(ValueError):
            obj = data_format(term=123, uri=None)



