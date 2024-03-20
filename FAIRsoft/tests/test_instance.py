import pytest
from FAIRsoft.classes.main import instance, software_types
from pydantic import HttpUrl, AnyUrl
class TestInstance:

    # Creating a valid instance object with all required fields.
    def test_valid_instance_with_all_required_fields(self):
        instance_obj = instance(
            name="example",
            type="cmd",
            version=["1.0"],
            label=["label1"],
            links=["https://foo.com/file.py"]
        )
        assert instance_obj.name == "example"
        assert instance_obj.type == "cmd"
        assert instance_obj.version == ["1.0"]
        assert instance_obj.label == ["label1"]
        assert instance_obj.links == [AnyUrl("https://foo.com/file.py")]

    # Creating an instance object with only required fields.
    def test_instance_with_only_required_fields(self):
        instance_obj = instance(
            name="example",
            type="cmd",
            version=["1.0"]
        )
        assert instance_obj.name == "example"
        assert instance_obj.type == "cmd"
        assert instance_obj.version == ["1.0"]
        assert instance_obj.label == []
        assert instance_obj.links == []

    # Creating an instance object with all fields set to their maximum length.
    def test_instance_with_maximum_length_fields(self):
        instance_obj = instance(
            name="a" * 100,
            type="cmd",
            version=["1.0"],
            label=["label1"],
            links=["https://foo.com/file.py"]
        )
        assert instance_obj.name == "a" * 100
        assert instance_obj.type == "cmd"
        assert instance_obj.version == ["1.0"]
        assert instance_obj.label == ["label1"]
        assert instance_obj.links == [AnyUrl("https://foo.com/file.py")]

    # Creating an instance object with an invalid name (empty string, None, integer, etc.).
    def test_instance_with_invalid_name(self):
        with pytest.raises(ValueError):
            instance_obj = instance(
                name="",
                type="cmd",
                version=["1.0"],
                label=["label1"],
                links=["https://foo.com/file.py"]
            )

    # Creating an instance object with an invalid type (not in the software list).
    def test_instance_with_invalid_type(self):
        with pytest.raises(ValueError):
            instance_obj = instance(
                name="example",
                type="invalid_type",
                version=["1.0"],
                label=["label1"],
                links=["https://foo.com/file.py"]
            )

    # Creating an instance object with an invalid version (not a string or integer).
    def test_instance_with_invalid_version(self):
        with pytest.raises(ValueError):
            instance_obj = instance(
                    name='name',
                    type="cmd",
                    version=None,
                    label=["label1"],
                    links=["https://foo.com/file.py"]
                )
    
    # Create instance where license is an empty list should work fine
    def test_instance_with_empty_license(self):
        instance_obj = instance(
                    name='name',
                    type="cmd",
                    version=["1.0"],
                    label=["label1"],
                    links=["https://foo.com/file.py"],
                    license=[]
                )
        assert instance_obj.license == []

class TestsoftwareTypes:

    # The class can be instantiated with any of the software types as a string.
    def test_instantiate_with_software_type(self):
        software_type = software_types('cmd')
        assert software_type == 'cmd'

    # The class can be compared for equality with another instance of the same class.
    def test_equality_with_same_instance(self):
        software_type1 = software_types('cmd')
        software_type2 = software_types('cmd')
        assert software_type1 == software_type2

    # The class can be used as a dictionary key.
    def test_use_as_dictionary_key(self):
        software_type = software_types('cmd')
        my_dict = {software_type: 'value'}
        assert my_dict[software_type] == 'value'

    # The class cannot be instantiated with a string that is not one of the software types.
    def test_instantiate_with_invalid_string(self):
        with pytest.raises(ValueError):
            software_types('invalid')

    # The class cannot be instantiated with a number.
    def test_instantiate_with_number(self):
        with pytest.raises(ValueError):
            software_types(123)

    # The class cannot be instantiated with a boolean.
    def test_instantiate_with_boolean(self):
        with pytest.raises(ValueError):
            software_types(True)

class TestEmptyName:

    # Providing a non-empty string as input should return the same string.
    def test_non_empty_string(self):
        instance_obj = instance(name="test", type="cmd", version=["1.0"])
        assert instance_obj.name == "test"
        assert instance_obj.type == "cmd"
        assert instance_obj.version == ["1.0"]
        assert instance_obj.label == []
        assert instance_obj.links == []

    # Providing a string with whitespace characters should return the same string.
    def test_string_with_whitespace(self):
        instance_obj = instance(name="test", type="cmd", version=2)
        assert instance_obj.name == "test"
        assert instance_obj.type == "cmd"
        assert instance_obj.version == ["2"]
        assert instance_obj.label == []
        assert instance_obj.links == []

    # Providing an empty string as input should raise a ValueError with the message "The name cannot be empty."
    def test_empty_string(self):
        with pytest.raises(ValueError):
            instance_obj = instance(name="", type="cmd", version=["1.0"])
            

class TestEDAMTopics:

    # Providing a non-empty list of a non empty string as input should return the same list.
    def test_valid_edam_topic(self):
        instance_obj = instance(name="test", type="cmd", version=["1.0"], edam_topics=["http://edamontology.org/topic_0003"])
        assert instance_obj.name == "test"
        assert instance_obj.type == "cmd"
        assert instance_obj.version == ["1.0"]
        assert instance_obj.label == []
        assert instance_obj.links == []
        assert instance_obj.edam_topics == [HttpUrl("http://edamontology.org/topic_0003")]


class TestDescriptions:

    def valid_description(self):

        instance_obj = instance(name="test", type="cmd", version=["1.0"], description=["this is a description"])
        assert instance_obj.name == "test"
        assert instance_obj.type == "cmd"
        assert instance_obj.version == ["1.0"]
        assert instance_obj.label == []
        assert instance_obj.links == []
        assert instance_obj.description == ["This is a description."]