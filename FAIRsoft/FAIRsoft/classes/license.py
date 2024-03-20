from pydantic import BaseModel, field_validator, HttpUrl, model_validator
from typing import Optional
from FAIRsoft.utils import connect_collection
import os
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
        if 'name' not in data and 'url' not in data:
            raise ValueError("At least one of the fields 'name' or 'url' must be present")
        else:
            if not data.get('name') and not data.get('url'):
                raise ValueError("At least one of the fields 'name' or 'url' must be present")
        
        return data
    
    @model_validator(mode="before")
    @classmethod
    def map_to_name_to_spdx(cls, data):
        '''Map to SPDX license if possible.'''
        if data.get('url') is None:
            # Map to SPDX
            collection = cls.connect_license_collection()
            matching_license = collection.find_one({ "$or": [ 
                                            { "licenseId": data['name'] }, 
                                            { "synonyms": data['name'] }, 
                                            {"name": data['name']} 
                                            ],
                                        "isDeprecatedLicenseId": False}, {"_id": 0, "reference": 1, "licenseId":1 } )

            if matching_license:
                data['name'] = matching_license['licenseId']
                data['url'] = matching_license['reference']
                
            
        return data
    
    @staticmethod
    def connect_license_collection():
        '''
        connect to the licenses collection in remote database and return the collection object
        '''
        licensesCollection = connect_collection(collection='licensesMapping')
        return(licensesCollection)

            
    
