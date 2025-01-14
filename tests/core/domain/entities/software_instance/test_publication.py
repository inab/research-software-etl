import pytest
from pydantic import ValidationError
from src.core.domain.entities.software_instance.publication import publication_item, mentions_year


def test_clean_doi_with_full_url():
    url = "https://doi.org/10.1093/bioinformatics/btx713"
    item = publication_item(doi=url)
    assert item.doi == "10.1093/bioinformatics/btx713", "DOI was not properly trimmed from the URL"

def test_clean_doi_with_doi_that_failed_before_modifications_in_regex():
    doi = "10.1186/s13321‐018‐0324‐5"
    item = publication_item(doi=doi)
    assert item.doi == doi, "DOI was altered unnecessarily"


def test_clean_doi_with_raw_doi():
    raw_doi = "10.1093/bioinformatics/btx713"
    item = publication_item(doi=raw_doi)
    assert item.doi == raw_doi, "DOI was altered unnecessarily"

def test_invalid_doi():
    invalid_doi = "invalid_doi"
    with pytest.raises(ValidationError):
        publication_item(doi=invalid_doi)

def test_empty_doi():
    item = publication_item(doi=None)
    assert item.doi is None, "Empty DOI was not handled correctly"

def test_other_fields():
    item = publication_item(
        cit_count=5,
        citations=[],
        doi="10.1093/bioinformatics/btx713",
        pmcid="PMC1234567",
        pmid="12345678",
        title="Sample Title",
        year=2023,
        ref_count=10,
        refs=[]
    )
    assert item.cit_count == 5, "Citation count is incorrect"
    assert item.title == "Sample Title", "Title is incorrect"
    assert item.pmcid == "PMC1234567", "PMCID is incorrect"
    assert item.pmid == "12345678", "PMID is incorrect"
    assert item.year == 2023, "Year is incorrect"
    assert item.ref_count == 10, "Reference count is incorrect"