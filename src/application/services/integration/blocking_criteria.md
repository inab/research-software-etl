## Grouping Criteria for Software Metadata Entries

Software metadata entries are grouped into candidate blocks prior to disambiguation using a hybrid approach that combines **name/type similarity** and **normalized repository/webpage links**. The grouping procedure uses a Union-Find-style algorithm to ensure transitive closure over linked entries.

### Grouping Keys

Each entry is assigned a grouping key based on:
- The **software name** (`name`, lowercased)
- The **software type** (`type`, or `"*"` if `None` or `"undefined"`)

This forms a grouping key of the form:

### Link Extraction and Normalization

Entries may contain repository or webpage links. These are extracted and normalized using the following rules:

- **Normalization**:
  - Remove protocol (`http://`, `https://`)
  - Remove trailing slashes
  - Lowercase the domain and path
  - Remove `.html` from Bioconductor pages
  - Collapse Bioconductor URLs to `bioconductor.org/packages/<pkg_name>`

- **Link types considered**:
  - Repositories (`repository.url`)
  - Webpages (`webpage[]`) that contain known repository-like domains:
    - `github.com`, `sourceforge.net`, `gitlab.com`, `bitbucket.org`
    - `bioconductor.org/packages`, `pypi.org/project/`, `metacpan.org/pod/`, `cran.r-project.org/package`

Only normalized links from these sources are considered for grouping.

### Grouping Logic

- Entries are grouped if:
  - They share the same `<name>/<type>` key and/or
  - They share **at least one normalized link** (repository or webpage)

- A **Union-Find** strategy is used to:
  - Merge groups that share links
  - Ensure transitive grouping (e.g., A~B and B~C implies A~C)

- Groups are merged by:
  - Promoting to the "main" key (first group encountered)
  - Updating link associations and group members

### Wildcard Handling

- Entries with `type: None` or `type: "undefined"` are treated as `"*"` to avoid over-fragmentation due to type gaps.

---

### Summary

This grouping procedure yields blocks of candidate entries that:
- Share either a name/type key or a normalized software URL
- Can be meaningfully disambiguated together using link-based or model-assisted strategies