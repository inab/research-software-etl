# Software entries integration

## 1. Overview
This document explains how we **integrate, merge, and deduplicate** software metadata from multiple sources, including GitHub, Bioconductor, Galaxy, and Biotools.

The integration process ensures that:
- 🟢 **Software entries from different sources referring to the same tool are merged**.
- 🔍 **Potential incorrect merges and inconsistencies are flagged for manual inspection**.
- ⚡ **The process is efficient, scalable, and minimizes manual work**.

We use **name/type similarities and repository links** to determine when two entries should be merged. Additionally, we flag **cases where different names share the same repository**, which may indicate naming inconsistencies.

## 2. Merging Criteria
We assume that two software entries **are the same** if they:
1. **Have the same name and type** (_e.g., `"RNA-SeqAnalyzer/tool"`_).
2. **Share a repository link or webpage** (_e.g., `"https://github.com/org/tool"`_).

Additionally, we flag cases where:
- **Two entries have different names but share the same repository link** (potential naming inconsistencies).
- **Two entries have the same name but different repository links** (possible duplication errors).

#### Why this approach?
✔ **Most tools have unique names** across sources.  
✔ **Most tools are hosted on a single main repository** (GitHub, Bioconductor, SourceForge, etc.).  
✔ **Different sources (e.g., Biotools, Galaxy) often reference the same tools but with different metadata**.  

#### Potential Issues
⚠ **Some tools might share a name but be completely different** (_e.g., `"FastQC/tool"` from Bioconductor vs. another `"FastQC"` in Galaxy_).  
⚠ **Some tools might exist under multiple links, making automatic grouping uncertain**.  
⚠ **Some tools might be listed under different names across sources** (_e.g., `"RNA-SeqAnalyzer"` vs. `"RNASeq-Analyzer"`_).  

To handle this, we **flag potential conflicts for manual review**.

## **3. How the Integration Works**
### **Step-by-Step Process**
1️. **Fetch software metadata from multiple sources**.  
2️. **Group entries using `name/type` as an initial key**.  
3️. **Extract all repository/webpage links for each software**.  
4️. **Merge entries that share a repository or webpage link**.  
5️. **Flag cases where:**
   - **Tools have the same name/type but different repository links**.
   - **Tools have different names but share the same repository link**.
6️. **Save results and flagged conflicts for manual review**.  


## 4. Grouping & Merging Algorithm
The integration is based on **grouping by `name/type` and repository links**, with an additional **conflict detection step**.

### Step 1: Grouping and Merging Entries
The goal of this step is to **identify when multiple software entries refer to the same tool** and group them together.  

Since different sources (e.g., **GitHub, Bioconductor, Biotools, Galaxy**) may list the same tool under **slightly different names or metadata**, we use a **combination of name/type and repository links** to determine when two entries belong to the same group.

#### How Grouping Works
1. **Each software entry is assigned a unique key based on `name/type`**  
   - This serves as the **initial grouping mechanism**.  
   - Example: `"RNA-SeqAnalyzer/tool"`, `"FastQC/tool"`  
   
2. **All repository URLs and webpage links for each entry are extracted.**  
   - These links **act as identifiers** for the software.  
   - Example:
     ```json
     {
       "name": "RNA-SeqAnalyzer",
       "type": "tool",
       "repository": ["https://github.com/org/rna-seq-analyzer"],
       "webpage": ["https://rnaseqanalyzer.com"]
     }
     ```
   - Extracted links:  
     ```
     {"https://github.com/org/rna-seq-analyzer", "https://rnaseqanalyzer.com"}
     ```

3. **New entries are either merged into an existing group or form a new group.**  
   - If **a new entry shares at least one repository link or webpage with an existing group**, it is **merged into that group**.  
   - Otherwise, it **forms a new group**.

---

#### 💡 Example: Grouping in Action
##### Given Two Software Entries
```json
{
  "name": "RNA-SeqAnalyzer",
  "type": "tool",
  "repository": ["https://github.com/org/rna-seq-analyzer"],
  "webpage": ["https://rnaseqanalyzer.com"]
},
{
  "name": "RNASeq-Analyzer",
  "type": "tool",
  "repository": ["https://github.com/org/rna-seq-analyzer"],
  "webpage": []
}
```
##### Step-by-Step Execution
1. **First entry (`RNA-SeqAnalyzer/tool`) creates a new group:**
   ```
   Group created:
   Key: "rna-seqanalyzer/tool"
   Links: {"https://github.com/org/rna-seq-analyzer", "https://rnaseqanalyzer.com"}
   ```

2. **Second entry (`RNASeq-Analyzer/tool`) has a matching repository link!**  
   ✅ **Merged into existing group**:
   ```
   Group Updated:
   Key: "rna-seqanalyzer/tool"
   Links: {"https://github.com/org/rna-seq-analyzer", "https://rnaseqanalyzer.com"}
   ```

---

#### Algorithm Breakdown (Simplified Pseudocode)
```python
grouped_instances = {}
link_to_keys = {}  # Map each link to a known software group

for entry in all_entries:
    key = f"{entry['name'].lower()}/{entry['type']}"
    links = extract_links(entry)

    # Check if this entry shares links with an existing group
    matching_keys = set()
    for link in links:
        if link in link_to_keys:
            matching_keys.update(link_to_keys[link])

    if matching_keys:
        # Merge into an existing group (pick first matching group as the primary one)
        main_key = next(iter(matching_keys))
        grouped_instances[main_key]['instances'].append(entry)
        grouped_instances[main_key]['links'].update(links)

        # Update all links to point to this merged group
        for link in links:
            link_to_keys[link] = main_key
    else:
        # Create a new group
        grouped_instances[key] = {"instances": [entry], "links": links}
        for link in links:
            link_to_keys[link] = key
```

**Reference:** See `group_by_key_with_links()` in the source code.


---

### Step 2: Detecting Potential Conflicts
To **prevent incorrect merges**, we **flag cases where**:
1. **Two entries have the same name/type but different repository links**.
2. **Two entries have different names but share the same repository link**.

#### Simplified Logic:
```python
# Flag same name/type but different links
for group in grouped_instances:
    if group has multiple different links:
        flag for review

# Flag different names but same links
for link in all_links:
    if multiple names use the same link:
        flag for review
```
**Reference:** See `potential_conflicts.json` and `name_mismatch_conflicts.json` generation in the source code.

---

## 5. Example Scenarios
| **Scenario** | **Expected Behavior** |
|-------------|----------------------|
| Two tools from different sources with the same name and shared links | ✅ Merged |
| Two tools from different sources with the same name but different links | ⚠ Flagged for review |
| A GitHub tool and a Bioconductor tool where the GitHub `source_url` matches Bioconductor’s repo | ✅ Merged |
| Two tools with different names but the same repository link | ⚠ Flagged for review |
| A completely unique tool with no shared links** | ❌ Not merged (remains separate) |


