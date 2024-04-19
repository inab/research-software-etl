from src.core.domain.entities.software_instance import SoftwareInstance
from src.core.domain.entities.metadata.pretools import Metadata
from pydantic import BaseModel, Field

class PretoolsEntryModel(BaseModel):
    '''
    Model for the pretools collection in the database.
    '''
    metadata: Metadata = Field(..., description="Metadata of the entry")
    data: SoftwareInstance = Field(..., description="Data of the entry")
