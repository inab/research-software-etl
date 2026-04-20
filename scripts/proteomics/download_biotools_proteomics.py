import json
import requests

ENDPOINT = "https://bio.tools/api/t"
BASE_PARAMS = {
    "collectionID": "Proteomics",
    "format": "json",
}


def fetch_all_tools():
    tools = []
    page = 1
    session = requests.Session()

    while True:
        params = BASE_PARAMS.copy()
        params["page"] = page

        print(f"Downloading page {page}")
        r = session.get(ENDPOINT, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()

        tools.extend(data.get("list", []))

        if not data.get("next"):
            break

        page += 1

    return tools


tools = fetch_all_tools()

with open("scripts/proteomics/biotools_proteomics_tools.json", "w", encoding="utf-8") as f:
    json.dump(tools, f, ensure_ascii=False, indent=2)

with open("scripts/proteomics/biotools_proteomics_tools.jsonl", "w", encoding="utf-8") as f:
    for tool in tools:
        f.write(json.dumps(tool, ensure_ascii=False) + "\n")