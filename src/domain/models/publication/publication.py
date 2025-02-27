from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import re


# ------------------ CITATIONS MODEL ------------------

class YearlyCitation(BaseModel):
    """Model for tracking citations per year."""
    year: int = Field(..., description="Year")
    count: int = Field(..., description="Citation count")


class CitationSource(BaseModel):
    """Model for tracking citations from a single source (Google Scholar, Semantic Scholar, etc.)."""
    source_id: str = Field(..., description="Unique ID from the citation source")
    total_citations: int = Field(default=0, description="Total number of citations")
    citations_per_year: List[YearlyCitation] = Field(default={}, description="Citations count per year")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last updated timestamp")


# ------------------ PUBLICATION METADATA ------------------

class Publication(BaseModel):
    """Stores publication metadata inside 'data' for consistency with software collection."""
    doi: Optional[str] = Field(pattern=r"10\.\d{4,9}\/[-._;()\/:a-zA-Z0-9]+", default=None, description="Digital Object Identifier")
    pmcid:  Optional[str] = Field(pattern=r"^PMC\d+$", default=None, description="PubMed Central ID")
    pmid:  Optional[str] = Field(pattern=r"^\d+$",  default=None, description="PubMed Central ID") 
    url: Optional[str] = Field(None, description="URL to the paper or publisher's page")
    title: str = Field(..., description="Title of the paper")
    abstract: Optional[str] = Field(None, description="Abstract of the paper")
    # authors: Optional[List[str]] = Field(None, description="List of authors")
    year: Optional[int] = Field(None, description="Year of publication")
    journal: Optional[str] = Field(None, description="Journal or conference name")
    citations: Optional[List[CitationSource]] = Field(None, description="Citation data from various sources")

    @field_validator('doi', mode="before")
    @classmethod
    def clean_doi(cls, value) -> str:
        """
        Ensures that the DOI is trimmed to exclude the URL if it is provided as a full DOI URL.
        """
        if value and value.startswith("https://doi.org/"):
            match = re.match(r"https://doi\.org/(.+)", value)
            if match:
                value = match.group(1)
        
        return value

