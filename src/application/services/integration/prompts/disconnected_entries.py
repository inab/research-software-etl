"""
This prompt is used for cases where there are: 
    - Several disconnected entries
    - One disconnected entry and one remaining entry
"""


prompt = """
### **Task: Software Metadata Integration**
I am integrating software metadata from multiple sources and need to determine whether different tool entries refer to the same software. Given metadata for several tools, analyze the provided attributes and group them by identity.

---

### **Input Format**
Each tool has the many metadata fields:

- **Id**: A unique identifier for the tool in its respective source.
- **Name**: The tool’s name.
- **Description**: A brief description of the tool.
- **Repository**: The URL of the tool's source code repository (if available).
- **Webpage**: The tool’s official webpage (if available).
- **Source**: The sources of the tool metadata.
- ...

---


### Processing Instructions
1. Compare the metadata of each tool, prioritizing repository URLs, webpages, names, and descriptions.

2. Determine if two or more entries refer to the same tool by checking:
   - Link similarity between repositories and webpages.
   - Description similarity.
   - README similarty.
   - Common publications.
   - Common authors.
   - Common organizations.
   - Any other thing you may consider relevant.


3. Return a structured dictionary containing:
   - `verdict`: 
     - "Yes" → If the entries refer to the same tool.
     - "No" → If the entries refer to different tools.
     - "Unclear" → Only if, after analyzing external content, the relationship remains ambiguous or insufficient for a decision.
   - `groups`: A list of ID lists, where each inner list contains IDs that refer to the same tool.
   - `message`: A textual explanation of the reasoning, including whether repository or webpage content was analyzed.

  ### Important: Return only the JSON dictionary as a string, with no additional text, explanations, or formatting.


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

