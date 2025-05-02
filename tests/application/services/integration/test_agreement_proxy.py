import pytest
from src.application.services.integration.disambiguation.proxy import decision_agreement_proxy

# messages from real case
messages = [{'role': 'user', 'content': '### Task: Software Metadata Verification\n\nI am integrating software metadata from multiple sources. I have two metadata entries that may or may not belong to the same software.\n\nYour task is to compare one entry against the other and determine whether they refer to the same tool.\n\n### Input Format\n\nYou will receive inputs in **multiple parts**. Each part may include:\n\n- JSON-formatted metadata for a software tool\n- Extracted content from the tool’s repository (e.g., README files) or webpage (e.g., HTML, project descriptions). **These contents are provided explicitly because you do not have internet access.** Treat all provided content as final and in-scope. Do not assume any external URLs can be accessed.\n\nThe two tools are introduced as:\n- `"The first software metadata_entry"` \n- `"The second software metadata_entry"` \n\n### Processing Instructions\n\n1. Compare the metadata of each tool, prioritizing:\n   - repository URLs\n   - webpages\n   - descriptions\n   - documentation content (e.g., README)\n   - authorship or contact info\n   - associated publications or citations\n\n2. **IMPORTANT**: The tool names are often the same across entries. This is expected and should **not be used alone** to decide if they refer to the same software.\n\n3. Carefully analyze the provided repository or webpage content. Look for:\n   - Link similarity (e.g., GitHub, SourceForge)\n   - Shared or related descriptions\n   - Overlapping contributors, emails, or institutions\n   - Common citations or programming languages\n   - Usage instructions or tool behavior that match\n\n4. Wait until the final message says:\n\n   **"All parts have been sent. Please now analyze the entries and provide the output as specified."**\n\nOnly then should you perform the analysis.\n\n5. Your response must be a Python dictionary with the following keys:\n   - `verdict`: one of `"Same"`, `"Different"`, or `"Unclear"`\n   - `explanation`: 2–3 sentences explaining your decision, based only on the provided data\n   - `confidence`: one of `"high"`, `"medium"`, or `"low"`\n   - `features`: a list of metadata features you relied on (e.g., `"repo match"`, `"shared authors"`)\n\nDo not use generic templates or placeholder text. Your answer must reflect the actual input.\n\n### Output Format\n\nUse this structure for your answer:\n\n```python\n{\n  "verdict": "<Same | Different | Unclear>",\n  "explanation": "<brief reasoning based on the actual data>",\n  "confidence": "<high | medium | low>",\n  "features": ["<feature1>", "<feature2>", "..."]\n}\n```'}, {'role': 'user', 'content': 'Tools known to be the **same software** - part 1:\n```json\n[\n  {\n    "id": "bioconda_recipes/ale/cmd/20180904,bioconda_recipes/ale-core/cmd/20220503",\n    "name": "ale",\n    "description": [\n      "ALE: Assembly Likelihood Estimator.",\n      "This package is designed to hold the core scoring functionality of ALE without the 10+ year old supplementary python plotting scripts."\n    ],\n    "repository": [\n      {\n        "url": "https://github.com/sc932/ALE",\n        "kind": "github",\n        "source_hasAnonymousAccess": null,\n        "source_isDownloadRegistered": null,\n        "source_isFree": null,\n        "source_isRepoAccessible": null\n      }\n    ],\n    "webpage": [\n      "https://github.com/sc932/ALE"\n    ],\n    "source": [\n      "bioconda_recipes"\n    ],\n    "license": [\n      {\n        "name": "NCSA",\n        "url": "https://spdx.org/licenses/NCSA.html"\n      }\n    ],\n    "authors": [],\n    "publication": [],\n    "documentation": [\n      {\n        "type": "installation_instructions",\n        "url": "https://bioconda.github.io/recipes/ale/README.html",\n        "content": null\n      },\n      {\n        "type": "general",\n        "url": "https://bioconda.github.io/recipes/ale/README.html",\n        "content": null\n      },\n      {\n        "type": "installation_instructions",\n        "url": "https://bioconda.github.io/recipes/ale-core/README.html",\n        "content": null\n      },\n      {\n        "type": "general",\n        "url": "https://bioconda.github.io/recipes/ale-core/README.html",\n        "content": null\n      }\n    ]\n  }\n]\n```'}, {'role': 'user', 'content': '**Disconnected tools** to be analyzed - part 1:\n```json\n[\n  {\n    "id": "biotools/ale/cmd/None",\n    "name": "ale",\n    "description": [\n      "Automated label extraction from GEO metadata."\n    ],\n    "repository": [],\n    "webpage": [\n      "https://github.com/wrenlab/label-extraction"\n    ],\n    "source": [\n      "biotools"\n    ],\n    "license": [],\n    "authors": [\n      {\n        "type": "Person",\n        "name": "Jonathan D. Wren",\n        "email": "jonathan-wren@omrf.org",\n        "maintainer": false,\n        "url": null,\n        "orcid": null\n      },\n      {\n        "type": "Person",\n        "name": "Jonathan D. Wren",\n        "email": "jdwren@gmail.com",\n        "maintainer": false,\n        "url": null,\n        "orcid": null\n      }\n    ],\n    "publication": [\n      {\n        "$oid": "67c7a9b6d3b8acd1a2f9bb26"\n      }\n    ],\n    "documentation": [\n      {\n        "type": "general",\n        "url": "https://github.com/wrenlab/label-extraction/blob/master/README.md",\n        "content": null\n      }\n    ]\n  }\n]\n```'}, {'role': 'user', 'content': "All parts have been sent. Please now analyze the entries and provide the output as specified. \n\nIMPORTANT: Return ONLY a valid Python dictionary with the following keys: 'verdict', 'explanation', 'confidence', and 'features'. Do NOT explanation, or extra commentary. This is a strict output constraint."}]


llama_4_diff="""
```python
{
  "verdict": "Different",
  "explanation": "The two software metadata entries have different descriptions, repository URLs, and authors. The first entry describes 'ALE: Assembly Likelihood Estimator' with a GitHub repository at https://github.com/sc932/ALE, while the second entry describes 'Automated label extraction from GEO metadata' with a GitHub repository at https://github.com/wrenlab/label-extraction.",
  "confidence": "high",
  "features": ["description mismatch", "repo mismatch", "author mismatch"]
}
```
"""

mixtral_diff ="""
```python

{
  "verdict": "Different",
  "explanation": "The two software entries have different descriptions and repository URLs, indicating that they are different tools. The first tool is an Assembly Likelihood Estimator, while the second tool is for Automated label extraction from GEO metadata.",
  "confidence": "high",
  "features": ["description difference", "repo URL difference"]
}
```
"""

llama_4_same ="""
```python
{
  "verdict": "Same",
  "explanation": "Despite slight wording differences, both entries appear to describe the same R package for RNA-seq normalization.",
  "confidence": "medium",
  "features": ["functional overlap", "language match"]
}
```
"""

mixtral_same ="""
```python
{
  "verdict": "Same",
  "explanation": "The core function of the tools is identical and their names are similar.",
  "confidence": "medium",
  "features": ["name match", "functional overlap"]
}
```
"""


# Different combinations of mocked responses
test_cases = [
    (
        llama_4_diff,
        mixtral_diff,
        "Different"
    ),
    (
        llama_4_same,
        mixtral_same,
        "Same"
    ),
    (
        llama_4_diff,
        mixtral_same,
        "disagreement"
    )
]

@pytest.mark.parametrize("mock_llama, mock_mixtral, expected_verdict", test_cases)
def test_decision_agreement_proxy_with_variants(monkeypatch, mock_llama, mock_mixtral, expected_verdict):
    def mock_query_huggingface_new(messages, model, provider):
        return mock_llama, {}

    def mock_query_openrouter(messages, model):
        return mock_mixtral, {}

    monkeypatch.setattr(
        "src.application.services.integration.disambiguation.proxy.query_huggingface_new",
        mock_query_huggingface_new
    )
    monkeypatch.setattr(
        "src.application.services.integration.disambiguation.proxy.query_openrouter",
        mock_query_openrouter
    )

    result = decision_agreement_proxy(messages)
    assert result["verdict"] == expected_verdict
    assert 'llama_4' in result
    assert 'mixtral' in result
    for model in ['llama_4', 'mixtral']:
        assert 'explanation' in result[model]
        assert 'features' in result[model]