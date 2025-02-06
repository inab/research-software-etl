from pydantic import BaseModel, model_validator, HttpUrl, AnyUrl, TypeAdapter
from enum import Enum
from typing import List, Optional, Any, Dict

from src.core.domain.entities.software_instance.EDAM_forFE import EDAMDict


###------------------------------------------------------------
### Classes to represent data formats
###------------------------------------------------------------

# FREE TEXT FORMAT ----------------------------------------------
class free_text_data_format(BaseModel, validate_assignment=True):
    '''
    Exmaple:
       {
            "term" : "txt",
            "uri" : null
        }
    '''
    term: str = ''
    uri: Optional[HttpUrl] = None
    

###--------------------------------------------------
#    DATA FORMAT CLASS
###--------------------------------------------------
    
class data_type(BaseModel, validate_assignment=True):
    '''
    Class to represent a data type. Example

    {   "vocabulary": "EDAM",
        "term": "Sequence",
        "uri": "http://edamontology.org/data_0006"
    },
                
    '''
    vocabulary : str = ''
    term : str = ''
    uri : Optional[HttpUrl] = None

    #------------------------------------------------------------
    # Merging data types
    #------------------------------------------------------------

    def merge(self, other: 'data_type') -> 'data_type':
        if not isinstance(other, data_type):
            raise ValueError("Cannot merge with a non-data_type object")

        # Prefer the non-empty vocabulary, term, and URI
        self.vocabulary = self.vocabulary or other.vocabulary
        self.term = self.term or other.term
        self.uri = self.uri or other.uri

        return self


class data_format(BaseModel, validate_assignment=True):
    '''
    Class to represent a data format. Example

    {   "vocabulary": "EDAM",
        "term": "Sequence format",
        "uri": "http://edamontology.org/format_1929",
        datatype: {
            "vocabulary": "EDAM",
            "term": "Sequence",
            "uri": "http://edamontology.org/data_0006"
        }
    },
                
    '''
    vocabulary : str = ''
    term : str = ''
    uri : Optional[HttpUrl] = None
    datatype : Optional[data_type] = None

    #------------------------------------------------------------
    # Merging data formats
    #------------------------------------------------------------

    def merge(self, other: 'data_format') -> 'data_format':
        if not isinstance(other, data_format):
            raise ValueError("Cannot merge with a non-data_format object")

        # Prefer the non-empty vocabulary, term, and URI
        self.vocabulary = self.vocabulary or other.vocabulary
        self.term = self.term or other.term
        self.uri = self.uri or other.uri

        # Merge the datatype if present
        if self.datatype and other.datatype:
            self.datatype = self.datatype.merge(other.datatype)
        elif other.datatype:
            self.datatype = other.datatype

        return self
    

    #------------------------------------------------------------
    # Dealing with free text formats
    #------------------------------------------------------------
    @staticmethod
    def normalize_text_formats(term: str):
        equivalencies = [
            ["Textual format", "TXT", "txt", "textual", "plain text format (unformatted)"],
            ["FASTA-like","fasta-like", "fasta-like format (text)"],
            ["TSV","Tabular", "tabular", "tabular format", "tabular format (text)", "tab"],
            ["FASTQ-sanger", "fastqsanger"],
            ["YAML", 'yml', 'yaml'],
        ]
        if term:
            for group in equivalencies:
                if term.lower().lstrip() in group:
                    format = group[0]
                    break
                else:
                    format = term.lstrip()
        else:
            format = ''
        
        return format
    
    @staticmethod
    def mapEDAMDict(term: str):
        '''
        term: free text string
        Maps a free text string to an EDAM term if the match is perfect.
        '''
        for key,value in EDAMDict.items():
            if term.lower().lstrip() == value.lower():
                return(key, value, 'EDAM')

        return('', term, '')


    @model_validator(mode="before")
    @classmethod
    def reformat_free_text_items(cls, data: Dict[str, Any]):
        
        try:
            obj = free_text_data_format.model_validate(data, strict=True)
        except:
            return data
        else:
            # if the format is not free text, return the data as is
            if data.get('vocabulary'):
                return data
            elif data.get('datatype'):
                return data
            
            # Normalize case/equivalencies and map to EDAM terms 
            format = cls.normalize_text_formats(obj.term)
            uri, term, vocabulary = cls.mapEDAMDict(format)

            # ! Only keep formats with perfect matches
            if vocabulary and uri:
                print(f'Free text format')
                # 3. Format normalization:
                return {
                    'vocabulary': vocabulary,
                    'term': term,
                    'uri': uri,
                    'datatype': None # We cannot know the datatype from the free text
                }
            
            else:
                return None
   




                


