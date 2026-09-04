"""
Merge each resolved block into a single tool entry.

Entries are built into a staging collection, not into the live one. That is what
lets a merged tool keep the ``_id`` of the tool it continues: the live collection
is still there to be read while the new one is being built, and only replaces it
once the run finishes. See ``application/services/integration/tool_identity.py``
for how an entry finds its ancestor.
"""

import copy
import json
import logging
from datetime import datetime

from pydantic import BaseModel

from application.services.integration.disambiguation.utils import load_dict_from_jsonl
from application.services.integration.tool_identity import (
    NewTool,
    assign_identities,
    content_hash,
    previous_tool_from_document,
)
from domain.models.software_instance.multitype_instance import multitype_instance
from domain.repositories import Repositories

logger = logging.getLogger("rs-etl-pipeline")


def pretty_print_model(model: BaseModel) -> None:
    print(model.model_dump_json(indent=4))


def pretty_print_dict(d):
    print(json.dumps(d, indent=4, sort_keys=True))


def convert_to_multi_type_instance(entry):
    instance_data_dict = entry['data']
    if instance_data_dict['type']:
        instance_data_dict['type'] = [instance_data_dict['type']]
    else:
        instance_data_dict['type'] = []
    
    instance_data_dict['other_names'] = []

    return multitype_instance(**instance_data_dict)


def merge_instances(instances):
    merged_instances = instances[0]
    for instance in instances[1:]:
        merged_instances = merged_instances.merge(instance)   

    return merged_instances 
        

def fetch_entry_from_db(entry_id, repos: Repositories):
    return repos.pretools.get_by_id(entry_id)


def collect_source_ids(disambiguated_blocks) -> set:
    """
    Every pretools id that ``build_entries`` will actually merge.

    Mirrors the block-selection logic in ``build_entries`` so the preload fetches
    exactly the entries that will be read -- no more, no less.
    """
    ids: set = set()
    for value in disambiguated_blocks.values():
        resolution = value.get("resolution")
        if resolution not in ("no_conflict", "merged", "partial"):
            continue
        ids.update(value.get("merged_entries") or [])
        if resolution == "partial" and len(value.get("unmerged_entries") or []) == 1:
            ids.update(value.get("unmerged_entries") or [])
    return ids


def resolve_entry(entry_id, pretools_by_id, repos: Repositories):
    """
    Return a pretools entry from the preloaded cache, falling back to a direct
    read if it was not preloaded.

    The entry is copied because ``convert_to_multi_type_instance`` mutates
    ``data`` in place and an id can appear in more than one block.
    """
    entry = pretools_by_id.get(entry_id)
    if entry is None:
        entry = fetch_entry_from_db(entry_id, repos)
    return copy.deepcopy(entry)





def prepare_for_db(entry, entries_ids):

    # make suere entries_ids is a list
    if not isinstance(entries_ids, list):
        entries_ids = [entries_ids]

    db_entry = {
        'source': entries_ids,
        # A fresh update time by default. `carry_identities_forward` rolls this
        # back to the previous run's value when the content fingerprint below
        # shows the tool did not actually change, so stages keyed on
        # `last_updated_at` (FAIR scores) recompute only what moved. Named to
        # mirror pretools (`created_at` / `last_updated_at`).
        "last_updated_at": datetime.now().isoformat(),
        "content_hash": content_hash(entry),
    }

    db_entry['data'] = entry

    return db_entry


def save_entry(metadata, repos: Repositories):
    """
    Write one merged entry into the staging collection.

    The entry carries its own ``_id`` -- inherited from the tool it continues, or
    freshly minted -- so this is an insert into an empty staging collection, not an
    upsert into a live one.
    """
    try:
        return repos.tools_staging.insert(metadata)
    except Exception:
        print(f"Error saving entry {metadata.get('_id')}.")
        pretty_print_dict(metadata)
        raise


def save_entries(documents, repos: Repositories, batch_size: int = 1000):
    """
    Write all merged entries into the staging collection in batches.

    A batched counterpart to ``save_entry``: one ``insert_many`` per chunk
    instead of one insert per document, which is what made the merge stage
    outrun a tunnel that stayed open only so long.
    """
    for start in range(0, len(documents), batch_size):
        repos.tools_staging.insert_many(documents[start : start + batch_size])


def merge_entries(entries_ids, pretools_by_id, repos: Repositories):
    # retrieve full entries from the preloaded cache (falling back to the db)
    entries = [resolve_entry(entry, pretools_by_id, repos) for entry in entries_ids]
    # Put type in list and validate entries as multitype_instance
    if bool(entries) == False:
        print("No entries")
        print(f"ids: {entries_ids}")
    instances = [convert_to_multi_type_instance(entry) for entry in entries]
    #print('Instances in entries_ids converted to multitype_instance.')

    # merge entries
    if len(instances) > 1:
        # merge instances
        #print(f"Merging {len(instances)} entries in entries_ids...")
        merged_instances = merge_instances(instances)
        #print('Entries in entries_ids merged.')
    else:
        merged_instances = instances[0]
        #print(f"Only one entry in entries_ids. No merging needed.")

    merged_entries = merged_instances.model_dump(mode="json")   

    return merged_entries


def build_entries(disambiguated_blocks, pretools_by_id, repos: Repositories, summary):
    """
    Merge every resolved block into a tool document, in memory.

    Nothing is written yet: identity is assigned across the whole set at once (a
    block cannot know which previous tool it continues without seeing what the
    other blocks claim), so every document has to exist before any is stored.

    Each entry is tagged with the block key it came from, which is what the
    identity pass uses as a stable tie-break.

    Source entries come from ``pretools_by_id``, preloaded in one query rather
    than one round-trip per id.
    """
    entries = []

    for key, value in disambiguated_blocks.items():
        try:
            resolution = value.get("resolution")

            if resolution in ("no_conflict", "merged", "partial"):
                merged_ids = value.get("merged_entries")
                entry = merge_entries(merged_ids, pretools_by_id, repos)
                entries.append((key, prepare_for_db(entry, merged_ids)))
                summary['n_inserted_entries'] += 1

                if resolution == "partial" and len(value.get("unmerged_entries")) == 1:
                    unmerged_ids = value.get("unmerged_entries")
                    entry = merge_entries(unmerged_ids, pretools_by_id, repos)
                    # A second tool out of the same block needs its own key.
                    entries.append((f"{key}#unmerged", prepare_for_db(entry, unmerged_ids)))
                    summary['n_inserted_entries'] += 1

                summary['n_processed'] += 1

            elif resolution == "unclear":
                summary['n_unclear'] += 1
            elif resolution == "manual_review_pending":
                summary['n_pending'] += 1

        except Exception:
            print(f"Error processing block {key}.")
            raise

    return entries


def carry_identities_forward(entries, repos: Repositories):
    """
    Give each merged entry the ``_id`` of the tool it continues.

    Reads the lineage of the *live* collection -- the one this run will replace --
    and matches on the pretools entries each tool was built from.
    """
    previous = [
        lineage
        for lineage in (
            previous_tool_from_document(document)
            for document in repos.tools.iter_lineage()
        )
        if lineage is not None
    ]

    assignment = assign_identities(
        (NewTool(key=key, sources=frozenset(document["source"])) for key, document in entries),
        previous,
    )

    now = datetime.now().isoformat()
    for key, document in entries:
        ancestor = assignment.inherited.get(key)
        if ancestor is not None:
            document["_id"] = ancestor.tool_id
            document["created_at"] = ancestor.created_at
            # A tool whose content matches the one it continues keeps that tool's
            # update time. Downstream stages skip when `last_updated_at` is
            # unchanged, so this is what stops every run from recomputing every
            # tool. A fresh update time is kept only when the content actually
            # moved (or when the ancestor predates content hashing, so its hash
            # is empty).
            if ancestor.content_hash and ancestor.content_hash == document.get("content_hash"):
                document["last_updated_at"] = ancestor.last_updated_at
        else:
            # No ancestor: a genuinely new tool. Leave _id unset and let MongoDB
            # mint one, exactly as it did before this feature existed. Stamp
            # created_at and last_updated_at at the same instant -- a tool first
            # seen now was also last updated now -- rather than leaving the
            # marginally earlier time prepare_for_db set a moment before.
            document["created_at"] = now
            document["last_updated_at"] = now

    return assignment


def merge_and_save_blocks(disambiguated_blocks_file, repos: Repositories):
    '''
    Merge entries if:
        - resolution == merged or resolution == no_conflict:
            - merge “merged entries”
        - resolution == partial:
            - merge “merged entries”
            - save entry in “unmerge_entry” if len == 1

    Entries are written to the staging collection, keeping the ids of the tools
    they continue. The live collection is untouched until the run is finalized.
    '''

    disambiguated_blocks = load_dict_from_jsonl(disambiguated_blocks_file)
    print('Disambiguated blocks loaded.')

    # Preload every source entry in one $in query instead of one round-trip per
    # id. Over a tunnel, the per-id fetches were the dominant cost.
    source_ids = collect_source_ids(disambiguated_blocks)
    pretools_by_id = repos.pretools.get_by_ids(source_ids)
    print(f'Preloaded {len(pretools_by_id)} of {len(source_ids)} source entries.')

    summary = {
        "N": len(disambiguated_blocks),
        "n_processed": 0,
        "n_inserted_entries": 0,
        "n_pending": 0,
        "n_unclear": 0,
    }

    entries = build_entries(disambiguated_blocks, pretools_by_id, repos, summary)

    assignment = carry_identities_forward(entries, repos)

    # A failed earlier run can leave documents behind in staging; they are not
    # this run's output and must not be promoted with it.
    if repos.tools_staging.exists():
        repos.tools_staging.drop()

    # Batch the inserts: one round-trip per chunk instead of one per document.
    documents = [document for _key, document in entries]
    save_entries(documents, repos)

    summary["identities"] = assignment.summary(total_new=len(entries))
    logger.info("Tool identities: %s", summary["identities"])

    return summary





