from pydantic import BaseModel, HttpUrl, model_validator, field_validator
from typing import Optional
import re
from src.domain.models.software_instance.EDAM_forFE import EDAMDict


class vocabularyItem(BaseModel):
    '''
    Class to represent a vocabulary item, like topics and operations.
    '''
    vocabulary : str = ''
    term : Optional[str] = None
    uri : Optional[HttpUrl] = None

    @field_validator('uri', mode="before")
    @classmethod
    def uri_none(cls, value):
        '''
        If URI is '', turn it into None before anything elso to prevent an error raising.
        '''
        if value == '':
            return None
        else:
            return value


    @model_validator(mode="before")
    @classmethod
    def uri_and_term_cannot_be_empty(cls, data):
        '''
        URI and term cannot be empty at the same time. If that is the case, raise an ERROR.
        '''
        if not data.get('uri') and not data.get('term'):
            raise ValueError("URI and term cannot be empty at the same time")
        else:
            return data
    
    # ----------------------------------------
    # Function to try to populate empty fields
    # ----------------------------------------
    @model_validator(mode="after")
    @classmethod
    def populate_from_edam_uris(cls, data):
        '''
        If there is no term, try to populate it from the EDAM dictionary.
        '''
        if not data.term:
            if data.uri.host == 'edamontology.org':
                data.vocabulary = 'EDAM'
                data.term = EDAMDict.get(str(data.uri))
            
        return data
    
    @staticmethod
    def get_EDAM_uri(term: str):
        '''
        Maps a free text string to an EDAM term if the match is perfect.
        term: free text string
        '''
        for key,value in EDAMDict.items():
            if term.lower().lstrip() == value.lower():
                return(key)

        return(None)

    @model_validator(mode="after")
    @classmethod
    def populate_EDAM_uri(cls, data):
        '''
        If there is no URI, try to populate it from the EDAM dictionary.
        '''
        if not data.uri:
            data.uri = HttpUrl(vocabularyItem.get_EDAM_uri(data.term))
            if data.uri:
                data.vocabulary = 'EDAM'
            
        return data
    
    # ----------------------------------------
    # Merge 
    # ----------------------------------------
    def merge(self, other: 'vocabularyItem') -> 'vocabularyItem':
        if not isinstance(other, vocabularyItem):
            raise ValueError("Cannot merge with a non-vocabularyItem object")
        
        # Ensure they are the same vocabulary item
        if self.is_same_vocabulary_item(other):
            # Merge vocabulary: Prefer non-empty vocabulary
            self.vocabulary = self.vocabulary or other.vocabulary
            
            # Merge term: Prefer non-empty term
            self.term = self.term or other.term
            
            # Merge URI: Prefer non-empty URI
            self.uri = self.uri or other.uri
            
        return self
    
    def is_same_vocabulary_item(self, other: 'vocabularyItem') -> bool:
        return (self.uri and self.uri == other.uri) or (self.term and self.term == other.term)

    
    @model_validator(mode="after")
    @classmethod
    def populate_EDAM_vocabulary(cls, data):
        '''
        If there is no vocabulary, try to populate it from the EDAM dictionary.
        '''
        if not data.vocabulary:
            if data.uri.host == 'edamontology.org':
                data.vocabulary = 'EDAM'
            
        return data


#---------------------------------------------
# Topic class. Inherits from vocabularyItem
#---------------------------------------------
    
class vocabulary_topic(vocabularyItem):
    '''
    specific to topics
    '''
    @model_validator(mode="after")
    @classmethod
    def uri_EDAM_topic(cls, data):
        '''
        Check EDAM URIs are well formed and are topics
        '''
        if data.vocabulary == 'EDAM':
          if data.uri.host != 'edamontology.org':
            raise ValueError("URI must be edamontology")
          elif bool(re.match(r'^/topic_\d{4}$', data.uri.path)) == False:
            raise ValueError("URI must correspond an EDAM topic")
            
        return data
    
    def merge(self, other: 'vocabulary_topic') -> 'vocabulary_topic':
        # Call the parent class merge method
        return super().merge(other)

#------------------------------------------------
# Operations class. Inherits from vocabularyItem
#------------------------------------------------
class vocabulary_operation(vocabularyItem):
    '''
    specific to operations
    '''

    @model_validator(mode="after")
    @classmethod
    def uri_EDAM_operation(cls, data):
        '''
        Check EDAM URIs are well formed and are topics
        '''
        if data.vocabulary == 'EDAM':
          if data.uri.host != 'edamontology.org':
            raise ValueError("URI must be edamontology")
          elif bool(re.match(r'^/operation_\d{4}$', data.uri.path)) == False:
            raise ValueError("URI must correspond an EDAM operation")
            
        return data
    
    def merge(self, other: 'vocabulary_operation') -> 'vocabulary_operation':
        # Call the parent class merge method
        return super().merge(other)

