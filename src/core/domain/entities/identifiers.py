from pydantic import BaseModel

class pretools_identifier(BaseModel):
    '''
    Identifier of entry in the pretools collection.
    '''
    source: str # Make it an enum
    name: str
    type: str # Make it an enum
    version: str

    def get_id(self):
        return(f'{self.source}/{self.name}/{self.type}/{self.version}')


class tools_identifier(BaseModel):
    '''
    Identifier of entry in the tools collection.
    '''
    name: str
    type: str # Make it an enum

    def get_id(self):
        return(f'{self.name}/{self.type}')
