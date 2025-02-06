from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
import re

class mentions_year(BaseModel):
    year: int
    count: str

class publication_item(BaseModel):
    cit_count: int = None
    citations : List[mentions_year] = []
    doi: Optional[str] = Field(pattern=r"10\.\d{4,9}\/[-._;()\/:a-zA-Z0-9]+", default=None)
    pmcid:  Optional[str] = Field(pattern=r"^PMC\d+$", default=None)
    pmid:  Optional[str] = Field(pattern=r"^\d+$",  default=None) 
    title: str = None
    year: int = None
    ref_count: int = None
    refs : List[mentions_year] = []

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

    
    def merge(self, other: 'publication_item') -> 'publication_item':
        if not isinstance(other, publication_item):
            raise ValueError("Cannot merge with a non-publication_item object")

        # Ensure they are the same publication
        if not self.is_same_publication(other):
            raise ValueError("Cannot merge publication items that do not reference the same publication (based on DOI, PMCID, or PMID)")

        # Merge cit_count: Prefer the higher citation count
        self.cit_count = max(self.cit_count, other.cit_count) if self.cit_count and other.cit_count else self.cit_count or other.cit_count

        # Merge citations: Combine citations, avoiding duplicates
        self.citations = self._merge_mentions(self.citations, other.citations)

        # Merge DOI: Should be the same, so no change needed
        # Merge PMCID: Should be the same, so no change needed
        # Merge PMID: Should be the same, so no change needed

        # Merge title: Prefer non-empty title, but they should be the same
        self.title = self.title or other.title

        # Merge year: Prefer the earliest year, but they should be the same
        self.year = self.year or other.year

        # Merge ref_count: Prefer the higher reference count
        self.ref_count = max(self.ref_count, other.ref_count) if self.ref_count and other.ref_count else self.ref_count or other.ref_count

        # Merge refs: Combine refs, avoiding duplicates
        self.refs = self._merge_mentions(self.refs, other.refs)

        return self

    def is_same_publication(self, other: 'publication_item') -> bool:
        return (self.doi and self.doi == other.doi) or (self.pmcid and self.pmcid == other.pmcid) or (self.pmid and self.pmid == other.pmid)

    def _merge_mentions(self, list1: List[mentions_year], list2: List[mentions_year]) -> List[mentions_year]:
        merged = {m.year: m for m in list1}
        for mention in list2:
            if mention.year in merged:
                if int(mention.count) > int(merged[mention.year].count):
                    merged[mention.year].count = mention.count
            else:
                merged[mention.year] = mention
        return list(merged.values())