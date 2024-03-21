from pydantic import BaseModel, Field
from typing import List, Optional


class mentions_year(BaseModel):
    year: int
    count: str

class publication_item(BaseModel):
    cit_count: int = None
    citations : List[mentions_year] = []
    doi: Optional[str] = Field(pattern=r"^10\.\d{4,9}/[-._;()/:a-zA-Z0-9]+$", default=None)
    pmcid:  Optional[str] = Field(pattern=r"^PMC\d{7}$", default=None)
    pmid:  Optional[str] = Field(pattern=r"^\d+$",  default=None) 
    title: str = None
    year: int = None
    ref_count: int = None
    refs : List[mentions_year] = []

    