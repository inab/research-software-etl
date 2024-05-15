from src.core.domain.entities.software_instance.main import instance
from src.core.domain.entities.metadata import Metadata, VersionedMetadata
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