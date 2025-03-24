"""
This prompt is used for cases where there are:
    - One disconnected entry and several remaining entries:

"""

prompt = """
### **Task: Software Metadata Verification**
I am integrating software metadata from multiple sources. I already know that a group of tools (under `"remaining"`) refer to the same software. However, I have another tool (under `"disconnected"`) that may or may not belong to this same group. Your task is to compare the **disconnected** entry against the **remaining** entries and determine whether they refer to the same tool.

---

### **Input Format (JSON)**
You will receive a JSON object with the following structure:

```json
{
  "remaining": [
    {
      "Id": "Id1",
      "Name": "ToolA",
      "Description": "A tool for X.",
      "Repository": "https://github.com/example/toolA",
      "Webpage": "https://toolA.com",
      ...
    },
    {
      "Id": "Id2",
      "Name": "ToolA v2",
      "Description": "A tool for X and Y.",
      "Repository": "https://github.com/example/toolA",
      "Webpage": "https://toolA.com",
      ...
    }
  ],
  "disconnected": {
    "Id": "Id3",
    "Name": "ToolB",
    "Description": "A different tool for Z.",
    "Repository": "https://github.com/example/toolB",
    "Webpage": "https://toolB.com",
    ...
  }
}
```

---

### **Processing Instructions**
1. **Compare the `"disconnected"` entry with the `"remaining"` tools** by analyzing:
   - Link similarity between repositories and webpages.
   - Description similarity.
   - README similarty.
   - Common publications.
   - Common authors.
   - Common organizations.
   - Any other thing you may consider relevant.

2. **Return a structured dictionary** containing:
   - **`verdict`**:
     - `"Yes"` → If the disconnected entry belongs to the same tool as the remaining group.
     - `"No"` → If the disconnected entry refers to a different tool.
     - `"Unclear"` → If there is not enough information to make a determination.
   - **`message`**: A textual explanation of the reasoning behind the decision.
   - **`groups`**:
     - If `"Yes"`, return a list with all IDs grouped together.
     - If `"No"`, return the `"remaining"` group separately from the `"disconnected"` entry.

  ### Important: Return only the JSON dictionary as a string, with no additional text, explanations, or formatting.


---

### **Handling 'Unclear' Cases**
If the **verdict is "Unclear"**, the LLM should **generate the body of a GitHub issue** to allow a human to review the case and make the final decision. The issue should contain:
- A brief summary of the conflict.
- The conflicting metadata entries.
- A request for a human review with a proposed resolution.

---

### **Expected Output Format**
The LLM should return a **Python dictionary** structured as follows:
```python
{
  "verdict": "Yes" | "No" | "Unclear",
  "groups": [
    ["Id1", "Id2"],  # Group of tools identified as the same
    ["Id3"]          # Another distinct tool
  ],
  "message": "Id1 and Id2 have identical repositories and webpages, confirming they refer to the same tool. Id3 has distinct metadata, so it is a different tool."
}
```

If the **verdict is "Unclear"**, the dictionary should also contain:
```python
{
  "verdict": "Unclear",
  "groups": [
    ["Id1", "Id2"],  # Potential match but needs verification
    ["Id3"]          # Clearly separate tool
  ],
  "message": "Id1 and Id2 have similar names and descriptions, but ....",
  "github_issue": {
    "title": "Disambiguation Needed: Possible Duplicate Tools (Id1, Id2)",
    "body": '''
    The following tools have similarities but lack definitive metadata to confirm they are the same:

    **Tool 1** 
    - Id: Id1
    - Name: ToolA
    - Description: A tool for X.
    - Repository: (None)
    - Webpage: https://toolA.com

    **Tool 2** 
    - Id: Id2
    - Name: ToolA v2
    - Description: A tool for X and Y.
    - Repository: https://github.com/example/toolA
    - Webpage: (None)

    Please verify whether these entries should be merged.
    '''
  }
}
```

### **Input**

Here are the entries to be analyzed: 
```json
{{ data | tojson(indent=2) }}
```

"""
