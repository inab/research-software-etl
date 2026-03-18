from __future__ import annotations

from typing import Any

from src.application.services.enrich_publications.helpers import extract_doi


def normalize_doi(raw_doi: Any) -> str | None:
    """
    Normalize a DOI string.

    - If it already starts with '10.', return it as-is.
    - Otherwise try to extract a DOI from the input string.
    - Return None if normalization fails.
    """
    if not isinstance(raw_doi, str):
        return None

    doi = raw_doi.strip()
    if not doi:
        return None

    if doi.startswith("10."):
        return doi

    extracted = extract_doi(doi)
    if not extracted:
        return None

    return extracted.strip()