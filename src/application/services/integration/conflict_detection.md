## Heuristics for Metadata Conflict Detection

To identify potentially conflicting metadata entries referring to the same software, we group entries by heuristic similarity and then apply a series of domain-specific rules to detect and refine conflicts. The following heuristics are applied:

### 1. Link-Based Conflict Detection

Entries grouped together are considered **conflicting** if they contain links (repository or webpage) but **do not share any normalized link**.

- Links are normalized by:
  - Removing protocol prefixes (`http://`, `https://`)
  - Removing trailing slashes and `.git`
  - Lowercasing the domain and path
  - Handling special cases (e.g., removing `.html` from Bioconductor URLs and collapsing them to a package-specific form)

Only entries with at least one normalized link are considered in this step.

---

### 2. No-Link Entry Handling

Entries that **do not have any repository or webpage link** are treated as follows:

- By default, they are considered **disconnected** (i.e., unknown identity).
- The heuristic `use_name_match_for_no_links` is set to `False`, meaning name similarity alone is not sufficient for grouping.

---

### 3. Galaxy Ecosystem Grouping

Entries from the Galaxy ecosystem (`"galaxy"`, `"toolshed"`, `"galaxy_metadata"`) are grouped together under the following rules:

- If **all entries in a group** are Galaxy-related and share the same name, the entire block is considered **non-conflicting** and is skipped.
- If **only some entries** are Galaxy-related and share the most common name, they are **promoted to `remaining`**, even if they lack links or are otherwise flagged as disconnected.

This rule captures trusted name equivalence within the Galaxy ecosystem.

---

### 4. Source + Name Merge Heuristic

After initial conflict detection, we apply a post-processing rule:

- If a `disconnected` entry shares the same `name` and at least one overlapping `source` with a `remaining` entry, it is moved to the `remaining` list.

This captures entries that are very likely to refer to the same software based on structured source identity.

---

### Summary

These heuristics balance high-precision grouping based on link sharing with fallback domain knowledge, helping to reduce over-splitting and guide downstream disambiguation by language models or human annotators.