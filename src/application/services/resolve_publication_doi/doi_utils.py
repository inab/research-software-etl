from __future__ import annotations


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None

    doi = doi.strip()

    prefixes = (
        "https://doi.org/",
        "http://doi.org/",
        "doi.org/",
        "doi:",
        "DOI:",
    )

    for prefix in prefixes:
        if doi.startswith(prefix):
            doi = doi[len(prefix):].strip()

    doi = doi.strip().lower()

    if not doi:
        return None

    return doi