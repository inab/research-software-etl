"""
Pretools documents for the four `ale` entries the disambiguation blocks refer to.

disambiguate_blocks() hydrates every conflict entry id into a full pretools
document. The conflict blocks in data_disambiguation_original.py were captured
from production and already carry the real field values, so the fixtures are
derived from them rather than invented: whatever the blocks say an entry's name,
description, repository and webpage are, that is what the pretools document says
too.

filter_relevant_fields() reads exactly the keys built below; the remaining
pretools fields are empty for these four entries.
"""

from tests.application.services.integration.data.data_disambiguation_original import (
    conflicts_blocks_sets,
)


def _url(link: str) -> str:
    """Blocks carry bare hosts ("github.com/sc932/ALE"); the models want a URL."""
    return link if "://" in link else f"https://{link}"


def _pretools_document(entry: dict) -> dict:
    """Turn a conflict-block entry into the pretools document it was hydrated from."""
    description = entry.get("description")
    return {
        "_id": entry["id"],
        "created_at": "2025-04-02T11:33:50.516346",
        "data": {
            "name": entry.get("name"),
            "type": entry.get("types"),
            "description": [description] if isinstance(description, str) else (description or []),
            # repository is a list of items, not of bare urls; the block flattens it.
            "repository": [{"url": _url(r)} for r in (entry.get("repository") or [])],
            "webpage": [_url(w) for w in (entry.get("webpage") or [])],
            "source": list(entry.get("source") or []),
            "license": [],
            "authors": [],
            "publication": [],
            "documentation": [],
        },
    }


def pretools_entries_for(*conflict_block_sets) -> list[dict]:
    """Every distinct entry the given conflict blocks refer to, as a pretools document."""
    documents: dict[str, dict] = {}
    for conflict_blocks in conflict_block_sets:
        for block in conflict_blocks.values():
            for group in ("disconnected", "remaining"):
                for entry in block.get(group, []):
                    documents[entry["id"]] = _pretools_document(entry)
    return list(documents.values())


def pretools_entries() -> list[dict]:
    """The entries the five original conflict cases refer to."""
    return pretools_entries_for(*conflicts_blocks_sets)
