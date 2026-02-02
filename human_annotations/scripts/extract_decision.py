import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

import requests


HUMAN_ANNOTATIONS_PATH = "human_annotations/human_conflicts_log.jsonl"


def add_jsonl_record(path, new_record):
    with open(path, 'a') as f:
            json.dump(new_record, f)
            f.write('\n')


@dataclass(frozen=True)
class GitHubContext:
    repo: str
    issue_number: str
    token: str

    @property
    def api_base(self) -> str:
        return f"https://api.github.com/repos/{self.repo}/issues/{self.issue_number}"

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
        }

    @property
    def issue_url(self) -> str:
        # return f"https://github.com/{self.repo}/issues/{self.issue_number}"
        return f"https://github.com/inab/research-software-etl/issues/{self.issue_number}"


def match_conflict_url(body: str) -> Optional[str]:
    # Anything that isn't a square closing bracket
    name_regex = r"[^]]+"
    # http:// or https:// followed by anything but a closing paren
    url_regex = r"http[s]?://[^)]+"

    # Markdown link: [name](url) with optional spaces inside parens
    markup_regex = r"\[({0})\]\(\s*({1})\s*\)".format(name_regex, url_regex)

    # Match the specific quoted line in the issue body
    # e.g. > Conflict File: [<url>](<url>)
    line_regex = r"^>\s*Conflict File:\s*" + markup_regex + r"\s*$"

    matches = re.findall(line_regex, body, flags=re.MULTILINE)
    if not matches:
        return None

    # matches is a list of tuples: (link_text, url)
    _link_text, url = matches[0]
    return url.strip()


def match_conflict_id(body: str) -> Optional[str]:
    m = re.search(r"^> Conflict Id:\s*(\S+)\s*$", body, flags=re.MULTILINE)
    return m.group(1) if m else None


def extract_issue_fields(issue_body: str) -> Tuple[str, str]:
    """
    Returns (conflict_id, conflict_file_url) or raises ValueError with a clear message.
    """
    conflict_id = match_conflict_id(issue_body)
    if not conflict_id:
        raise ValueError("Conflict Id not found in issue body")

    conflict_file_url = match_conflict_url(issue_body)
    if not conflict_file_url:
        raise ValueError("Conflict File URL not found in issue body")

    return conflict_id, conflict_file_url


def build_record(conflict_id: str, conflict_file_url: str) -> Dict[str, Any]:
    return {
        "conflict_id": conflict_id,
        "date": datetime.now(timezone.utc).isoformat(),
        "conflict_name": conflict_id.split("_")[-1],
        "conflict_url": conflict_file_url,
    }


def fetch_issue_body(ctx: GitHubContext) -> str:
    issue = requests.get(ctx.api_base, headers=ctx.headers, timeout=30).json()
    return issue.get("body", "") or ""


def fetch_comments(ctx: GitHubContext) -> list[dict]:
    return requests.get(f"{ctx.api_base}/comments", headers=ctx.headers, timeout=30).json()


def parse_latest_json_block_from_comments(comments: list[dict]) -> Tuple[Optional[dict], str]:
    """
    Walk comments from newest -> oldest and try to parse the first JSON code block.
    Returns (data, error_message). If data is not None, error_message is "".
    """
    json_error = "No JSON block found in any comment."

    for comment in reversed(comments):
        body = comment.get("body", "") or ""

        matches = re.findall(r"```json\s*\n(.*?)```", body, re.DOTALL)
        if not matches:
            continue

        try:
            data = json.loads(matches[0])
            return data, ""
        except Exception as e:
            json_error = f"Error: {e}"

    return None, json_error


def post_comment(ctx: GitHubContext, text: str) -> None:
    payload = {"body": text}
    requests.post(
        f"{ctx.api_base}/comments",
        headers=ctx.headers,
        data=json.dumps(payload),
        timeout=30,
    )


def reopen_issue(ctx: GitHubContext) -> None:
    reopen_payload = {"state": "open"}
    requests.patch(
        ctx.api_base,
        headers=ctx.headers,
        data=json.dumps(reopen_payload),
        timeout=30,
    )


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print("Usage: script.py <repo> <issue_number>", file=sys.stderr)
        return 2

    repo = argv[1]
    issue_number = argv[2]

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Missing GITHUB_TOKEN env var", file=sys.stderr)
        return 2

    ctx = GitHubContext(repo=repo, issue_number=issue_number, token=token)

    # Fetch body
    body = fetch_issue_body(ctx)

    try:
        conflict_id, conflict_file_url = extract_issue_fields(body)
    except ValueError as e:
        post_comment(ctx, f"⚠️ {e}")
        reopen_issue(ctx)
        print(json.dumps({"error": str(e)}))
        return 1

    record = build_record(conflict_id, conflict_file_url)

    # Fetch comments + parse JSON decision
    comments = fetch_comments(ctx)
    data, json_error = parse_latest_json_block_from_comments(comments)

    if data is not None:
        data["issue_url"] = ctx.issue_url
        record["decision"] = data

        add_jsonl_record(HUMAN_ANNOTATIONS_PATH, record)
        return 0

    # Parsing failed: comment + reopen
    post_comment(
        ctx,
        "⚠️ Failed to parse a valid JSON decision block from this issue.\n"
        f"Error: `{json_error}`\n\n"
        "Please ensure the format is correct:\n"
        "```json\n{ ... }\n```",
    )
    reopen_issue(ctx)
    print(json.dumps({"error": "No valid decision found"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))