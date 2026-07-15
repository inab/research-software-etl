from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from application.services.resolve_publication_doi.doi_utils import normalize_doi


class CrossrefDoiResolutionService:
    """
    Picks the Crossref record that a title (and maybe a journal and a year) refers to.

    The matching is the interesting part and lives here; the HTTP call belongs to
    `CrossrefClient`, which the CLI hands in.
    """

    def __init__(
        self,
        client,
        rows: int = 5,
        min_confidence: float = 0.92,
    ) -> None:
        self.client = client
        self.rows = rows
        self.min_confidence = min_confidence

    def resolve(
        self,
        title: str,
        journal: str | None = None,
        year: int | None = None,
    ) -> dict[str, Any] | None:
        candidates = self._query_crossref(title=title, journal=journal)

        if not candidates:
            return None

        best: dict[str, Any] | None = None
        best_score = 0.0

        for item in candidates:
            candidate_title = self._extract_title(item)
            candidate_journal = self._extract_journal(item)
            candidate_year = self._extract_year(item)
            candidate_doi = normalize_doi(item.get("DOI"))

            if not candidate_title or not candidate_doi:
                continue

            score = self._score_candidate(
                input_title=title,
                input_journal=journal,
                input_year=year,
                candidate_title=candidate_title,
                candidate_journal=candidate_journal,
                candidate_year=candidate_year,
            )

            if score > best_score:
                best_score = score
                best = {
                    "doi": candidate_doi,
                    "source": "crossref",
                    "confidence": round(score, 4),
                    "matched_title": candidate_title,
                    "matched_journal": candidate_journal,
                    "matched_year": candidate_year,
                }

        if best and best["confidence"] >= self.min_confidence:
            return best

        return None

    def _query_crossref(self, title: str, journal: str | None = None) -> list[dict[str, Any]]:
        query = title.strip()
        if journal and str(journal).strip():
            query = f"{query} {journal.strip()}"

        return self.client.search_works(query, rows=self.rows)

    @staticmethod
    def _extract_title(item: dict[str, Any]) -> str | None:
        titles = item.get("title", [])
        if not titles:
            return None
        return str(titles[0]).strip()

    @staticmethod
    def _extract_journal(item: dict[str, Any]) -> str | None:
        journals = item.get("container-title", [])
        if not journals:
            return None
        return str(journals[0]).strip()

    @staticmethod
    def _extract_year(item: dict[str, Any]) -> int | None:
        for field in ("published-print", "published-online", "issued", "created"):
            value = item.get(field)
            if not value:
                continue

            date_parts = value.get("date-parts")
            if date_parts and date_parts[0]:
                year = date_parts[0][0]
                if isinstance(year, int):
                    return year

        return None

    def _score_candidate(
        self,
        input_title: str,
        input_journal: str | None,
        input_year: int | None,
        candidate_title: str,
        candidate_journal: str | None,
        candidate_year: int | None,
    ) -> float:
        title_score = self._similarity(
            self._normalize_text(input_title),
            self._normalize_text(candidate_title),
        )

        journal_score = 0.0
        if input_journal and candidate_journal:
            journal_score = self._similarity(
                self._normalize_text(input_journal),
                self._normalize_text(candidate_journal),
            )

        year_score = 0.0
        if input_year is not None and candidate_year is not None:
            year_score = 1.0 if int(input_year) == int(candidate_year) else 0.0

        if input_journal and input_year is not None:
            return (0.75 * title_score) + (0.15 * journal_score) + (0.10 * year_score)

        if input_journal:
            return (0.85 * title_score) + (0.15 * journal_score)

        if input_year is not None:
            return (0.90 * title_score) + (0.10 * year_score)

        return title_score

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.lower().strip().split())

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()