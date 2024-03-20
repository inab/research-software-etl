from FAIRsoft.classes.license import license_item    
from pydantic import HttpUrl, ValidationError
import pytest

#------------------------------------------------------------
# Test Class license
#------------------------------------------------------------


class TestLicense:

    # Creating a license object with a name and URL
    def test_create_license_with_name_and_url(self):
        license_obj = license_item(name="Test License", url="https://example.com")
        assert license_obj.name == "Test License"
        assert license_obj.url == HttpUrl("https://example.com")

    # Creating a license object with only a name
    def test_create_license_with_only_name(self):
        license_obj = license_item(name="Test License")
        assert license_obj.name == "Test License"
        assert license_obj.url is None

    # Cleaning the name of a license object by removing leading and trailing spaces
    def test_clean_name_removes_spaces(self):
        license_obj = license_item(name="  Test License  ")
        assert license_obj.name == "Test License"

    # Creating a license object with an empty name
    def test_create_license_with_empty_name(self):
        with pytest.raises(ValidationError):
            license_obj = license_item(name="")

    # Creating a license object with an invalid URL
    def test_create_license_with_invalid_url(self):
        with pytest.raises(ValueError):
            license_obj = license_item(name="Test License", url="invalid_url")
        
    # Creating a license object with no name or url
    def test_create_license_with_no_name_or_url(self):
        with pytest.raises(ValueError):
            license_obj = license_item(name='', url='')

    # Mapping a license object to an SPDX license with no matching name, synonym, or license ID
    def test_map_to_spdx_no_matching_license(self, mocker):
        license_obj = license_item(name="Test License")
        assert license_obj.name == "Test License"
        assert license_obj.url is None

    # Mapping a license object to an SPDX license with a matching name
    def test_matching_license(self):
        license_obj = license_item(name="MIT")
        print(license_obj)
        assert license_obj.name == "MIT"
        print(license_obj)
        assert license_obj.url == HttpUrl("https://spdx.org/licenses/MIT.html")
    
     # Mapping a license object to an SPDX license with a matching name
    def test_matching_license_wLICENSE(self):
        license_obj = license_item(name="MIT + LICENSE")
        assert license_obj.name == "MIT"
        assert license_obj.url == HttpUrl("https://spdx.org/licenses/MIT.html")

    # Some license with no matching SPDX license
    def test_non_matching_license(self):
        license_obj = license_item(name="Some license")
        assert license_obj.name == "Some license"
        assert license_obj.url == None
