"""
Application use case support: process publication metadata during transformation.

This module contains the publication-specific part of the transformation
workflow. It extracts publication references from raw source entries,
standardizes them into the internal publication representation, checks whether
matching publication records already exist, and creates new publication entries
when needed.

Its role is to ensure that transformed software metadata can be linked to
normalized publication records without duplicating publications already stored
in the database.
"""

import logging
from typing import Dict, Any, Optional, List
from application.services.publications.metadata import create_new_metadata
from infrastructure.config import PipelineConfig
from domain.repositories import PublicationRepository, Repositories
from application.services.publications.publication_standardizer_factory import StandardizerFactory
from application.services.publications.publication_extractor_factory import ExtractorFactory

logger = logging.getLogger("rs-etl-pipeline")

# Sources whose raw entries carry publication references.
SOURCES_W_PUBLICATION = [
    "bioconductor",
    "biotools",
    "toolshed",
    "opeb_metrics",
    "bioconda_recipes",
]

# The identifying fields, in the precedence `publication_in_collection` uses to
# match an incoming publication against one already stored.
_MATCH_FIELDS = ["doi", "title", "url", "pmid", "pmcid"]


def publication_in_collection(publication: Dict[str, Any], publications_repo: PublicationRepository) -> Optional[str]:
    '''
    Checks if the publication is already in the publications collection.
    - publication: publication to be checked
    - publications_repo: the publications collection
    '''
    # Check doi
    if publication.get('doi'):
        entry = publications_repo.find_by_doi(publication.get('doi'))
        if entry:
            return entry['_id']

    # Check title 
    if publication.get('title'):
        entry = publications_repo.find_by_title(publication.get('title'))
        if entry:
            return entry['_id']

    # Check URL 
    if publication.get('url'):
        entry = publications_repo.find_by_url(publication.get('url'))
        if entry:
            return entry['_id']

    # Check pmid 
    if publication.get('pmid'):
        entry = publications_repo.find_by_pmid(publication.get('pmid'))
        if entry:
            return entry['_id']

    # Check pmcid
    if publication.get('pmcid'):
        entry = publications_repo.find_by_pmcid(publication.get('pmcid'))
        if entry:
            return entry['_id']

    return None


def add_publication(
    publication: Dict[str, Any],
    publications_repo: PublicationRepository,
    config: PipelineConfig,
) -> str:
    '''
    Add a publication to the publications collection.
    - publication: publication to be added
    - publications_repo: the publications collection
    - config: run provenance for the entry metadata
    '''
    # Generate entry metadata
    metadata_dict = create_new_metadata(config.ci)

    # Build entry to insert in database
    metadata_dict['data'] = publication

    # Insert in database
    logger.debug(f"Adding publication {metadata_dict['data']['title']} to the publications collection.")
    id = publications_repo.save_entry(metadata_dict)
    return id



def standardize_publications(
    source_name: str,
    publications_ids,
    raw_publication_dict: Dict[str, Any],
    config: PipelineConfig,
    repos: Repositories,
) -> List[str]:
    publications_repo = repos.publications

    # Parse the entry
    publication_standardizer = StandardizerFactory.get_standardizer(source_name)
    standardized_publication = publication_standardizer.standardize(raw_publication_dict)
    if not standardized_publication:
        return publications_ids
    else:
        standardized_publication_dict = standardized_publication.model_dump()

    # Check if the publication is already in the publications collection
    publication_id = publication_in_collection(standardized_publication_dict, publications_repo)
    if publication_id:
        publications_ids.add(publication_id)
    else:
        publication_id = add_publication(standardized_publication_dict, publications_repo, config)
        publications_ids.add(publication_id)

    return publications_ids


def extract_publications(source_name : str, raw_entry : Dict) -> List[str]:

    publication_extractor = ExtractorFactory.get_extractor(source_name)
    publications = publication_extractor.extract_publications(raw_entry)

    return publications


def _match_key(publication: Dict[str, Any]):
    """The first non-empty identifying field of a publication, in match precedence,
    used to dedupe new publications within a page. ``None`` when the publication has
    no identity at all (so it can never be deduped against another)."""
    for field in _MATCH_FIELDS:
        if publication.get(field):
            return (field, publication[field])
    return None


def resolve_publications_for_page(
    raw_entries: List[Dict[str, Any]],
    source_name: str,
    config: PipelineConfig,
    repos: Repositories,
) -> List[List[Any]]:
    """
    Resolve the publications of a whole page of raw entries in a handful of
    round-trips instead of several per entry.

    Returns a list aligned with ``raw_entries``; each element is the list of
    publication ids (``ObjectId``) that entry cites. Semantics match the per-entry
    path (`standardize_publications` + `publication_in_collection`): an existing
    publication is reused, matched by doi → title → url → pmid → pmcid; an unmatched
    one is inserted. New publications are de-duped within the page so two entries
    citing the same new reference insert it once.
    """
    n = len(raw_entries)
    if source_name not in SOURCES_W_PUBLICATION:
        return [[] for _ in range(n)]

    publications_repo = repos.publications
    standardizer = StandardizerFactory.get_standardizer(source_name)

    # 1. Extract + standardize every publication in memory (no DB), keeping each
    #    tied to the entry it came from.
    flat: List[tuple] = []  # (entry_index, standardized_publication_dict)
    for i, entry in enumerate(raw_entries):
        for raw_publication in extract_publications(source_name, entry):
            standardized = standardizer.standardize(raw_publication)
            if standardized:
                flat.append((i, standardized.model_dump()))

    per_entry_ids: List[set] = [set() for _ in range(n)]
    if not flat:
        return [[] for _ in range(n)]

    # 2. One `$in` query per identifying field over the whole page.
    existing_maps: Dict[str, Dict[Any, Any]] = {}
    for field in _MATCH_FIELDS:
        values = [pub.get(field) for _, pub in flat if pub.get(field)]
        field_map: Dict[Any, Any] = {}
        for doc in publications_repo.find_existing_by_field(field, values):
            key = doc.get("data", {}).get(field)
            if key and key not in field_map:
                field_map[key] = doc["_id"]  # ObjectId, deliberately not stringified
        existing_maps[field] = field_map

    def resolve_existing(pub: Dict[str, Any]):
        for field in _MATCH_FIELDS:
            value = pub.get(field)
            if value and value in existing_maps[field]:
                return existing_maps[field][value]
        return None

    # 3. Resolve each publication; stage the unmatched ones for a single insert,
    #    de-duping within the page.
    resolved: List[Any] = [None] * len(flat)
    new_docs: List[Dict[str, Any]] = []
    docindex_by_key: Dict[Any, int] = {}
    docindex_by_pos: Dict[int, int] = {}
    unique_counter = 0

    for pos, (_, pub) in enumerate(flat):
        existing_id = resolve_existing(pub)
        if existing_id is not None:
            resolved[pos] = existing_id
            continue

        key = _match_key(pub)
        if key is None:
            key = ("__no_identity__", unique_counter)
            unique_counter += 1
        if key not in docindex_by_key:
            metadata = create_new_metadata(config.ci)
            metadata["data"] = pub
            docindex_by_key[key] = len(new_docs)
            new_docs.append(metadata)
        docindex_by_pos[pos] = docindex_by_key[key]

    # 4. One insert for every new publication on the page.
    new_ids = publications_repo.save_many(new_docs) if new_docs else []
    for pos in docindex_by_pos:
        resolved[pos] = new_ids[docindex_by_pos[pos]]

    # 5. Fold ids back onto their entries (a set dedupes within an entry, as before).
    for pos, (entry_index, _) in enumerate(flat):
        per_entry_ids[entry_index].add(resolved[pos])

    return [list(ids) for ids in per_entry_ids]
    
    
        

                
        