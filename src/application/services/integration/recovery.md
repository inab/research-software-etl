## Recovery Step: Merging Groups with Shared Links and Same Name

After initial grouping based on name/type keys and shared repository/webpage links, a recovery step is applied to merge blocks that may have been incorrectly split.

This step ensures transitive closure over links and groups entries that likely refer to the same software but ended up in separate blocks due to intermediate inconsistencies.

### 1. Detect Shared Links Across Groups

- All normalized links (from `repository.url` and `webpage[]`) are mapped to the group keys they appear in.
- **Links that appear in more than one group** are flagged as potentially connecting those groups.

### 2. Filter Groups with Same Name

From the shared-link connections, only group sets where **all group keys share the same `name`** (i.e., prefix before `/type`) are considered valid merge candidates.

> This ensures that groups are only merged if the link suggests identity *and* the names align.

### 3. Resolve Overlapping Group Memberships

In cases where some group keys appear in **multiple merge candidate sets**, those sets are:
- Merged into one consolidated group
- Deduplicated
- Replaced in the merge list

This prevents duplicate merging and guarantees a clean union of all connected groups.

### 4. Generate New Group Keys

For each merged group, a new key is created:

- Format: `name/type` if all types match
- Otherwise: `name/*` to indicate type ambiguity

### 5. Update the Grouped Instances

The original groups are removed, and the new merged group (with the new key) is added to the `grouped_instances` dictionary.

---

### Summary

This recovery step captures and merges previously missed groupings where:

- Two or more groups **share a normalized link**
- The associated entries **have the same software name**
- The original grouping step did not detect the equivalence due to structure or metadata variability

By resolving these fragments, this step improves the completeness and accuracy of the disambiguation blocks.