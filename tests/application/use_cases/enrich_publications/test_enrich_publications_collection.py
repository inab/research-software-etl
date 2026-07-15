"""Tests for the publication-enrichment use case.

Pins the §4.1 behaviour: a Europe PMC citation entry whose ``count`` is
total-only (``{"total": N}``, no per-year keys) still needs enrichment and must
not be treated as done. ~5 356 documents (17% of those with citations) were in
that state; the scheduled job re-enriches them to obtain the yearly breakdown.
"""

from __future__ import annotations

from application.use_cases.enrich_publications.enrich_publications_collection import (
    EnrichPublicationCollectionUseCase,
)
from tests.fakes import FakeDatabaseAdapter, fake_repos

_PREDICATE = EnrichPublicationCollectionUseCase._has_europe_pmc_yearly_citations


def _epmc(count: dict) -> dict:
    return {"data": {"citations": [{"source": "Europe PMC", "count": count}]}}


def test_total_only_count_needs_enrichment():
    """A total-only count is NOT a completed enrichment."""
    assert _PREDICATE(_epmc({"total": 5})) is False


def test_yearly_breakdown_is_done():
    """A per-year breakdown means enrichment already happened."""
    assert _PREDICATE(_epmc({"2021": 3, "2022": 2, "total": 5})) is True


def test_non_europe_pmc_citations_need_enrichment():
    doc = {"data": {"citations": [{"source": "Other", "count": {"2021": 1}}]}}
    assert _PREDICATE(doc) is False


def test_no_citations_need_enrichment():
    assert _PREDICATE({"data": {}}) is False


class _FakeEnrichmentService:
    """Returns a per-year breakdown and records which DOIs it was asked about."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def enrich_by_doi(self, doi: str) -> dict:
        self.calls.append(doi)
        return {
            "citations": [{"source": "Europe PMC", "count": {"2021": 1, "total": 1}}]
        }


class _FakeCache:
    def __init__(self) -> None:
        self.appended: list[dict] = []

    def load_seen_dois(self) -> set[str]:
        return set()

    def append(self, payload: dict) -> None:
        self.appended.append(payload)

    def clear(self) -> None:  # pragma: no cover - not exercised here
        pass


def test_execute_reenriches_total_only_and_skips_yearly():
    """End-to-end over a fake repo: total-only is re-enriched, yearly is skipped."""
    total_only = {
        "_id": "total-only",
        "data": {
            "doi": "10.1/total-only",
            "citations": [{"source": "Europe PMC", "count": {"total": 5}}],
        },
    }
    already_done = {
        "_id": "yearly",
        "data": {
            "doi": "10.1/yearly",
            "citations": [{"source": "Europe PMC", "count": {"2020": 5, "total": 5}}],
        },
    }
    db = FakeDatabaseAdapter({"publications": [total_only, already_done]})
    repos = fake_repos(db, publications=True)
    service = _FakeEnrichmentService()

    use_case = EnrichPublicationCollectionUseCase(
        publication_repository=repos.publications,
        enrichment_cache=_FakeCache(),
        enrichment_service=service,
    )

    use_case.execute(collection_name="publications")

    # Only the total-only record was sent for enrichment.
    assert service.calls == ["10.1/total-only"]

    # Its citations now carry a per-year breakdown in the DB.
    stored = db.fetch_entry("publications", "total-only")
    assert stored["data"]["citations"][0]["count"] == {"2021": 1, "total": 1}

    # The record that already had a yearly breakdown was left untouched.
    untouched = db.fetch_entry("publications", "yearly")
    assert untouched["data"]["citations"][0]["count"] == {"2020": 5, "total": 5}
