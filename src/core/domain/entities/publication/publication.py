from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime



# ------------------ CITATIONS MODEL ------------------

class CitationSource(BaseModel):
    """Model for tracking citations from a single source (Google Scholar, Semantic Scholar, etc.)."""
    source_id: str = Field(..., description="Unique ID from the citation source")
    total_citations: int = Field(default=0, description="Total number of citations")
    citations_per_year: Dict[int, int] = Field(default={}, description="Citations count per year")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last updated timestamp")


class PublicationCitations(BaseModel):
    """Stores citation data inside 'data' for consistency with software collection."""
    sources: Dict[str, CitationSource] = Field(default={}, description="Dictionary of sources (Google Scholar, Semantic Scholar, etc.)")


# ------------------ PUBLICATION METADATA ------------------

class Publication(BaseModel):
    """Stores publication metadata inside 'data' for consistency with software collection."""
    doi: Optional[str] = Field(None, description="Digital Object Identifier")
    url: Optional[str] = Field(None, description="URL to the paper or publisher's page")
    pmid: Optional[str] = Field(None, description="PubMed ID")
    pmcid: Optional[str] = Field(None, description="PubMed Central ID")
    title: str = Field(..., description="Title of the paper")
    abstract: Optional[str] = Field(None, description="Abstract of the paper")
    authors: Optional[List[str]] = Field(None, description="List of authors")
    published_year: Optional[int] = Field(None, description="Year of publication")
    journal: Optional[str] = Field(None, description="Journal or conference name")
    citations: Optional[PublicationCitations] = Field(None, description="Citation data from various sources")

