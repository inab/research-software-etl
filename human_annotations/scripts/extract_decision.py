# .github/scripts/extract_decision.py
import requests, sys, os, re, json

print("Running extract_decision.py")

repo = sys.argv[1]
issue_number = sys.argv[2]
token = os.environ['GITHUB_TOKEN']
url = f"https://api.github.com/repos/{repo}/issues/{issue_number}/comments"

headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github+json"
}


comments = requests.get(url, headers=headers).json()

for comment in reversed(comments):
    matches = re.findall(r"```json\n(.*?)\n```", comment['body'], re.DOTALL)
    if matches:
        try:
            data = json.loads(matches[0])
            print(json.dumps(data))
            sys.exit(0)
        except json.JSONDecodeError:
            continue

print(json.dumps({"error": "No valid decision found"}))
sys.exit(0)