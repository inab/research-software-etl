
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional


class source_item(BaseModel):
    collection: str = Field(..., description="Collection of the source")
    id: str = Field(..., description="Id of the source")

    source_url : Optional[HttpUrl] = Field(None, description="URL of the source") # generally, only available for github, sourceforge and bioconductor


class source_items_list(BaseModel):
    collection : str = Field(..., description="Collection of the source")
    ids: List[str] = Field(..., description="List of ids of the source")


class Metadata(BaseModel):
    '''
    Metadata of entries after transformation.
    It goes in the "pretools" collection. Example of metadata object:
    {
        "id": "toolshed/trimal/cmd/1.4",
        "created_at": "2023-01-01T00:00:00Z", 
        "created_by": "https://gitlab.bsc.es/inb/elixir/software-observatory/bioconductor-imoprter-v2/-/commit/180347cb5bae6b553663a670a560e13c40f1e64f",
        "created_logs": "https://gitlab.bsc.es/oeb-research-software/oeb-research-software/-/pipelines/1234",
        "last_updated_at": "2023-02-01T12:00:00Z",
        "updated_by": "https://gitlab.bsc.es/inb/elixir/software-observatory/bioconductor-imoprter-v2/-/commit/180347cb5bae6b553663a670a560e13c40f1e64f",
        "updated_logs": "https://gitlab.bsc.es/oeb-research-software/oeb-research-software/-/pipelines/1235",
        "source":  {
            "collection": "tools",
            "id": "toolshed/trimal/cmd/1.4",
            "source_url": "http://github.com/foo/bar"
        }
    }
    '''
    id: str = Field(..., description="Identifier of the entry in the database. It is transform to _id right before insertion.")
    created_at: str = Field(..., description="Creation date of the entry", alias='created_at')
    created_by: str = Field(..., description="User or task that created the entry", alias='created_by')
    created_logs: str = Field(..., description="Link to the logs of the creation process", alias='created_logs')
    last_updated_at: str = Field(..., description="Last update of the entry", alias='last_updated_at')
    updated_by: str = Field(..., description="User or task that updated the entry", alias='updated_by')
    updated_logs: str = Field(..., description="Link to the logs of the last update", alias='updated_logs')
    source: List[source_item] = Field(..., description="Sources of the entry", alias='source') # only one source!
    

    def to_dict_for_db_insertion(self):
        '''
        Returns a dictionary with the metadata fields for insertion in the database.
        The fields are the same as the ones in the class, but prefixed by a "@".
        '''
        metadata_for_db = {}
        for field in self.model_fields:
            metadata_for_db['@'+field] = getattr(self, field)
        
        return metadata_for_db


class VersionedMetadata(Metadata):
    """
    Represents a versioned metadata entity.

    Attributes:
        version (int): The version number of the metadata.
    """
    version: int
    source: source_items_list = Field(..., description="Source of the entry", alias='@source')
