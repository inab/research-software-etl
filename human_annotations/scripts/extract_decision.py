import requests, sys, os, re, json
from src.application.services.integration.disambiguation.utils import add_jsonl_record

repo = sys.argv[1]
issue_number = sys.argv[2]
conflict_id = sys.argv[3]

token = os.environ['GITHUB_TOKEN']
api_base = f"https://api.github.com/repos/{repo}/issues/{issue_number}"
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json"
}

# Fetch comments
comments = requests.get(f"{api_base}/comments", headers=headers).json()

json_error = "No JSON block found in any comment."
human_annotations_path = 'human_annotations/human_conflicts_log.jsonl'
# Try to parse a JSON block from comments
for comment in reversed(comments):
    print("---- COMMENT BODY ----")
    print(comment['body'])

    matches = re.findall(r"```json\s*\n(.*?)```", comment['body'], re.DOTALL)
    print("Matches found:", len(matches))

    if matches:
        try:
            print("Trying to load JSON block:")
            print(matches[0])
            data = json.loads(matches[0])
            data['issue_url'] = f"https://github.com/inab/research-software-etl/issues/{issue_number}"
            
            record = { conflict_id : data }
            add_jsonl_record(human_annotations_path, record)
 
            sys.exit(0)
        except Exception as e:
            json_error = f"Error: {e}"

# If we reach here, parsing failed
comment_payload = {
    "body": f"⚠️ Failed to parse a valid JSON decision block from this issue.\nError: `{json_error}`\n\nPlease ensure the format is correct:\n```json\n{{ ... }}\n```"
}
requests.post(f"{api_base}/comments", headers=headers, data=json.dumps(comment_payload))

# Reopen the issue
reopen_payload = {"state": "open"}
requests.patch(api_base, headers=headers, data=json.dumps(reopen_payload))

print(json.dumps({"error": "No valid decision found"}))
sys.exit(1)