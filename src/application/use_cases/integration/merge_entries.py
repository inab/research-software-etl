"""
Merge each resolved block into a single tool entry.

Entries are built into a staging collection, not into the live one. That is what
lets a merged tool keep the ``_id`` of the tool it continues: the live collection
is still there to be read while the new one is being built, and only replaces it
once the run finishes. See ``application/services/integration/tool_identity.py``
for how an entry finds its ancestor.
"""

import json
import logging
from datetime import datetime

from pydantic import BaseModel

from application.services.integration.disambiguation.utils import load_dict_from_jsonl
from application.services.integration.tool_identity import (
    NewTool,
    assign_identities,
    previous_tool_from_document,
)
from domain.models.software_instance.multitype_instance import multitype_instance
from infrastructure.db.repositories import Repositories

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





def prepare_for_db(entry, entries_ids):

    # make suere entries_ids is a list
    if not isinstance(entries_ids, list):
        entries_ids = [entries_ids]

    db_entry = {
        'source': entries_ids,
        "timestamp": datetime.now().isoformat()
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


def merge_entries(entries_ids, repos: Repositories):
    # retrieve full entries from db
    entries = [fetch_entry_from_db(entry, repos) for entry in entries_ids]
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


def build_entries(disambiguated_blocks, repos: Repositories, summary):
    """
    Merge every resolved block into a tool document, in memory.

    Nothing is written yet: identity is assigned across the whole set at once (a
    block cannot know which previous tool it continues without seeing what the
    other blocks claim), so every document has to exist before any is stored.

    Each entry is tagged with the block key it came from, which is what the
    identity pass uses as a stable tie-break.
    """
    entries = []

    for key, value in disambiguated_blocks.items():
        try:
            resolution = value.get("resolution")

            if resolution in ("no_conflict", "merged", "partial"):
                merged_ids = value.get("merged_entries")
                entry = merge_entries(merged_ids, repos)
                entries.append((key, prepare_for_db(entry, merged_ids)))
                summary['n_inserted_entries'] += 1

                if resolution == "partial" and len(value.get("unmerged_entries")) == 1:
                    unmerged_ids = value.get("unmerged_entries")
                    entry = merge_entries(unmerged_ids, repos)
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
            document["first_seen"] = ancestor.first_seen
        else:
            # No ancestor: a genuinely new tool. Leave _id unset and let MongoDB
            # mint one, exactly as it did before this feature existed.
            document["first_seen"] = now

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

    summary = {
        "N": len(disambiguated_blocks),
        "n_processed": 0,
        "n_inserted_entries": 0,
        "n_pending": 0,
        "n_unclear": 0,
    }

    entries = build_entries(disambiguated_blocks, repos, summary)

    assignment = carry_identities_forward(entries, repos)

    # A failed earlier run can leave documents behind in staging; they are not
    # this run's output and must not be promoted with it.
    if repos.tools_staging.exists():
        repos.tools_staging.drop()

    for _key, document in entries:
        save_entry(document, repos)

    summary["identities"] = assignment.summary(total_new=len(entries))
    logger.info("Tool identities: %s", summary["identities"])

    return summary





