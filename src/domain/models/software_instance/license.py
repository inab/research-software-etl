from pydantic import BaseModel, field_validator, HttpUrl, model_validator
from typing import Optional

# TODO: THe mapping using a remote database needs to be moved to a service
# from core.utils import connect_collection


class license_item(BaseModel, validate_assignment=True):
    name: str = None # optional, non-nullable
    url: Optional[HttpUrl] = None # optional, nullable

    @field_validator('name', mode="after")
    @classmethod
    def clean_name(cls, value) -> str:
        '''Removes leading and trailing spaces from the name.'''
        value = value.rstrip('.')
        return value.strip()
    
    @field_validator('name', mode="after")
    @classmethod
    def remove_file_LICENSE(cls, value) -> str:
        ''' remove the file LICENSE from the license name '''
        # remove +, LICENSE and file LICENSE
        value = value.replace('+', '')
        value = value.replace('LICENSE', '')
        value = value.replace('file', '')
        value = value.replace('File', '')
        value = value.replace('FILE', '')

        value = value.strip()

        return value

    @model_validator(mode="before")
    @classmethod
    def one_must_be_not_empty(cls, data):
        
        '''At least one of the fields 'name' or 'url' must be present.'''
        '''
        if 'name' not in data and 'url' not in data:
            raise ValueError("At least one of the fields 'name' or 'url' must be present")
        else:
            if not data.get('name') and not data.get('url'):
                raise ValueError("At least one of the fields 'name' or 'url' must be present")
        '''
        return data
    
    """
    @model_validator(mode="before")
    @classmethod
    def map_to_name_to_spdx(cls, data):
        '''Map to SPDX license if possible.
        TODO: This needs to be moved to a service, it does not belong to a model.
        '''
        from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter

        if data.get('url') is None:
            # Map to SPDX
            query = { "$or": [ 
                            { "licenseId": data['name'] }, 
                            { "synonyms": data['name'] }, 
                            {"name": data['name']} 
                        ],
                        "isDeprecatedLicenseId": False}
            matching_license = mongo_adapter.fetch_entry('licensesMapping', query)

            if matching_license:
                data['name'] = matching_license['licenseId']
                data['url'] = matching_license['reference']     
            
        return data
    """
    
    def merge(self, other: 'license_item') -> 'license_item':
        if not isinstance(other, license_item):
            raise ValueError("Cannot merge with a non-license_item object")
        
        # Merge names: Prefer SPDX-mapped name if available
        if self.name != other.name:
            if 'SPDX' in self.name and 'SPDX' not in other.name:
                merged_name = self.name
            elif 'SPDX' in other.name and 'SPDX' not in self.name:
                merged_name = other.name
            else:
                merged_name = self.name or other.name
        else:
            merged_name = self.name
        
        # Merge URLs: Prefer non-null URL
        merged_url = self.url or other.url

        return license_item(name=merged_name, url=merged_url)

            
    
