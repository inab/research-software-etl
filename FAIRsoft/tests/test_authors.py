from FAIRsoft.classes.recognition import contributor, type_contributor
from pydantic import ValidationError
import pytest

class TestContributor:

    # Create a new contributor with required fields.
    def test_create_new_contributor_required_fields(self):
        # Arrange
        data = {
            'type': 'Person',
            'name': 'John Doe'
        }
    
        # Act
        result = contributor(**data)
    
        # Assert
        assert result.type == type_contributor.Person
        assert result.name == 'John Doe'
        assert result.email is None
        assert result.maintainer is False

    # Create a new contributor with all fields.
    def test_create_new_contributor_all_fields(self):
        # Arrange
        data = {
            'type': 'Organization',
            'name': 'Example Organization',
            'email': 'example@example.com',
            'maintainer': True
        }
    
        # Act
        result = contributor(**data)
    
        # Assert
        assert result.type == type_contributor.Organization
        assert result.name == 'Example Organization'
        assert result.email == 'example@example.com'
        assert result.maintainer is True

    # Create a new contributor with only name and email fields.
    def test_create_new_contributor_name_email_fields(self):
        # Arrange
        data = {
            'name': 'Jane Smith',
            'email': 'jane@example.com'
        }
    
        # Act
        result = contributor(**data)
    
        # Assert
        assert result.type == None
        assert result.name == 'Jane Smith'
        assert result.email == 'jane@example.com'
        assert result.maintainer is False

    # Create a new contributor with an invalid email.
    def test_create_new_contributor_invalid_email(self):
        # Arrange
        data = {
            'type': 'Person',
            'name': 'John Doe',
            'email': 'invalid_email'
        }
    
        # Act & Assert
        with pytest.raises(ValueError):
            contributor(**data)

    # Create a new contributor with an invalid type.
    def test_create_new_contributor_invalid_type(self):
        # Arrange
        data = {
            'type': 'invalid_type',
            'name': 'John Doe'
        }
    
        # Act & Assert
        with pytest.raises(ValueError):
            contributor(**data)

    # Create a new contributor with an empty name.
    def test_create_new_contributor_empty_name(self):
        # Arrange
        data = {
            'type': 'Person',
            'name': ''
        }
    
        # Act & Assert
        with pytest.raises(ValidationError):
            contributor(**data)

    # Create a new contributor with an empty name.
    def test_create_new_contributor_invalid_name(self):
        # Arrange
        data = {
            'type': 'Contributors',
            'name': ''
        }
    
        # Act & Assert
        with pytest.raises(ValidationError):
            contributor(**data)