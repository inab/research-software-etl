from src.domain.models.software_instance.main import instance
from src.domain.models.metadata import Metadata, VersionedMetadata
from pydantic import BaseModel, Field

class PretoolsEntryModel(BaseModel):
    '''
    Model for the pretools collection in the database.
    '''
    metadata: Metadata = Field(..., description="Metadata of the entry")
    data: instance = Field(..., description="Data of the entry")


class ToolEntryModel(BaseModel):
    '''
    Model for the tools collection in the database.
    '''
    metadata: VersionedMetadata = Field(..., description="Metadata of the entry")
    data: instance = Field(..., description="Data of the entry")

class PublicationEntryModel(BaseModel):
    '''
    Model for the publications collection in the database.
    '''
    metadata: Metadata = Field(..., description="Metadata of the entry")
    data: instance = Field(..., description="Data of the entry")