from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# ------------------ PUBLICATION ENTRY METADATA ------------------

class Metadata(BaseModel):
    '''
    Metadata of publication entries.
    It goes in the "publications" collection. Example of metadata object:
    {
        "created_at": "2023-01-01T00:00:00Z", 
        "created_by": "https://gitlab.bsc.es/inb/elixir/software-observatory/bioconductor-imoprter-v2/-/commit/180347cb5bae6b553663a670a560e13c40f1e64f",
        "created_logs": "https://gitlab.bsc.es/oeb-research-software/oeb-research-software/-/pipelines/1234",
        "last_updated_at": "2023-02-01T12:00:00Z",
        "updated_by": "https://gitlab.bsc.es/inb/elixir/software-observatory/bioconductor-imoprter-v2/-/commit/180347cb5bae6b553663a670a560e13c40f1e64f",
        "updated_logs": "https://gitlab.bsc.es/oeb-research-software/oeb-research-software/-/pipelines/1235",
    }
    '''
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the entry was created")
    created_by: Optional[str] = Field(None, description="Reference to the entity that created this entry")
    created_logs: Optional[str] = Field(None, description="Logs or pipelines related to the creation")
    last_updated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the entry was last updated")
    updated_by: Optional[str] = Field(None, description="Reference to the entity that last updated this entry")
    updated_logs: Optional[str] = Field(None, description="Logs or pipelines related to the last update")


