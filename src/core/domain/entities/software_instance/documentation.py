from pydantic import BaseModel, model_validator, HttpUrl, TypeAdapter
from enum import Enum
from typing import List, Optional, Any, Dict


###------------------------------------------------------------
### Classes to represent documentation
###------------------------------------------------------------

# Documentation item class  -----------------------------------------

class documentation_item(BaseModel):
    '''
    Documentation item in intance class.
    '''
    type: str = 'general' # optional, non-nullable
    url : Optional[HttpUrl] = None # optional, nullable
    content: Optional[str] = None # optional, nullable


    @model_validator(mode="before")
    @classmethod
    def if_simple_docs(cls, data: Dict[str, Any]):
        '''
        A common format is [type, url].
        Transform to a dictionary like {'type': type, 'url': url}
        '''
        if isinstance(data, list):
            if len(data) == 2:
                if isinstance(data[0], str) and isinstance(data[1], str):
                    return {'type': data[0], 'url': data[1]}
        
        return data
    
    @model_validator(mode="before")
    @classmethod
    def replace_documentation_type(cls, data: Dict[str, Any]):
        '''
        Replace the type 'documentation' with 'general'
        '''
        if data:
            if 'type' in data:
                if data['type'] == 'documentation':
                    data['type'] = 'general'
        
        return data
    
    def merge(self, other: 'documentation_item') -> 'documentation_item':
        if not isinstance(other, documentation_item):
            raise ValueError("Cannot merge with a non-documentation_item object")

        # Merge 'type': prefer the most specific type
        if self.type == 'general' and other.type != 'general':
            self.type = other.type

        # Merge 'url': prefer the non-null URL
        self.url = self.url or other.url

        # Merge 'content': prefer the longer or more detailed content
        if not self.content or (other.content and len(other.content) > len(self.content)):
            self.content = other.content

        return self
        


