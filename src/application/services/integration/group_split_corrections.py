import json
import logging
from collections import defaultdict
from pathlib import Path


logger = logging.getLogger("rs-etl-pipeline")

def normalize_source_name_stem(instance_id: str) -> str | None:
    """
    Extract <source>/<name> from a full instance id.

    Examples:
    - biotools/histone_coder/app/1 -> biotools/histone_coder
    - sourceforge/protms/None/None -> sourceforge/protms
    """
    if not instance_id:
        return None

    parts = [p.strip().lower() for p in str(instance_id).split("/") if p.strip()]
    if len(parts) >= 2:
        return f"{parts[0]}/{parts[1]}"
    return None


def load_split_corrections(corrections_file: str | Path) -> list[set[str]]:
    """
    Load manual split corrections from JSON.

    Expected format:
    [
      ["biotools/histone_coder", "biotools/isoscale"],
      ["biotools/quant", "biotools/wiff2dta", "sourceforge/protms"]
    ]
    """
    path = Path(corrections_file)

    if not path.exists():
        logger.warning("Split corrections file not found: %s. Continuing without corrections.", path)
        return []

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    corrections = []
    for i, group in enumerate(raw, start=1):
        if not isinstance(group, list):
            logger.warning("Skipping invalid correction at index %d: expected list, got %r", i, type(group))
            continue

        stems = {
            normalize_source_name_stem(item)
            for item in group
            if normalize_source_name_stem(item)
        }

        if len(stems) >= 2:
            corrections.append(stems)
        else:
            logger.warning("Skipping correction at index %d: fewer than 2 valid stems", i)

    logger.info(
        "Loaded %d split-correction groups from %s",
        len(corrections),
        path,
    )
    for i, correction in enumerate(corrections, start=1):
        logger.debug("Split correction %d: %s", i, sorted(correction))

    return corrections


def build_instance_identity_index(instances: list[dict]) -> dict[str, list[dict]]:
    """
    Group instances by normalized <source>/<name> stem.
    """
    by_identity = defaultdict(list)

    for inst in instances:
        inst_id = inst.get("_id")
        stem = normalize_source_name_stem(inst_id)
        if stem:
            by_identity[stem].append(inst)
        else:
            logger.warning("Could not extract source/name stem from instance id: %r", inst_id)

    return dict(by_identity)


def make_split_group_key(base_group_key: str, stem: str, used_keys: set[str]) -> str:
    """
    Create a stable new key for a split subgroup.

    Prefer:
    - <name>/<type> if base group had one type and no collision
    - otherwise <name>/*_split
    - if needed, append _2, _3, ...

    stem is expected to be <source>/<name>.
    """
    _, _, name = stem.partition("/")
    candidate = f"{name}/*"

    if candidate == base_group_key:
        candidate = f"{name}/*_split"

    if candidate not in used_keys:
        used_keys.add(candidate)
        return candidate

    counter = 2
    while True:
        next_candidate = f"{candidate}_{counter}"
        if next_candidate not in used_keys:
            used_keys.add(next_candidate)
            return next_candidate
        counter += 1


def split_group_by_manual_corrections(
    group_key: str,
    group_data: dict,
    correction_sets: list[set[str]],
    used_keys: set[str],
) -> dict[str, dict]:
    """
    Split one group if it contains identities that are manually declared incompatible.

    Returns a dict of one or more groups:
    - {original_key: original_group_data} if no split needed
    - {new_key1: {...}, new_key2: {...}, ...} if split applied
    """
    instances = group_data.get("instances", [])
    if len(instances) <= 1:
        return {group_key: group_data}

    by_identity = build_instance_identity_index(instances)
    present_identities = set(by_identity.keys())

    # Find correction sets that intersect this group in 2+ identities
    triggered_sets = []
    for correction in correction_sets:
        overlap = present_identities & correction
        if len(overlap) >= 2:
            triggered_sets.append(overlap)

    if not triggered_sets:
        return {group_key: group_data}

    # Merge overlapping triggered correction subsets transitively
    merged_triggers = []
    for overlap in triggered_sets:
        current = set(overlap)
        new_merged = []
        for existing in merged_triggers:
            if current & existing:
                current |= existing
            else:
                new_merged.append(existing)
        new_merged.append(current)
        merged_triggers = new_merged

    # Build output groups:
    # - each conflicting identity gets its own subgroup
    # - everything else is preserved in a remainder group
    conflicting_identities = set().union(*merged_triggers)

    new_groups = {}

    # Remainder instances: identities not part of the manual split
    remainder_instances = []
    for stem, stem_instances in by_identity.items():
        if stem not in conflicting_identities:
            remainder_instances.extend(stem_instances)

    if remainder_instances:
        new_groups[group_key] = {"instances": remainder_instances}

    for stem in sorted(conflicting_identities):
        new_key = make_split_group_key(group_key, stem, used_keys)
        new_groups[new_key] = {"instances": by_identity[stem]}

    logger.info(
        "Manual split applied to group %s: %d incompatible identities separated into %d groups",
        group_key,
        len(conflicting_identities),
        len(new_groups),
    )

    return new_groups


def apply_manual_split_corrections(
    grouped_instances: dict,
    corrections_file: str | Path,
) -> dict:
    """
    Apply manual split corrections to grouped instances.

    If a final group contains identities declared incompatible in the corrections file,
    split them into separate groups.
    """
    correction_sets = load_split_corrections(corrections_file)
    if not correction_sets:
        return grouped_instances

    corrected = {}
    used_keys = set(grouped_instances.keys())

    for group_key, group_data in grouped_instances.items():
        split_result = split_group_by_manual_corrections(
            group_key=group_key,
            group_data=group_data,
            correction_sets=correction_sets,
            used_keys=used_keys,
        )
        corrected.update(split_result)

    logger.info(
        "Manual split corrections complete. Groups before: %d, after: %d",
        len(grouped_instances),
        len(corrected),
    )

    return corrected