#!/usr/bin/env python3
"""
Add a comment + label to open issues tagged with "conflict" (excluding PRs), then close them.

Requirements:
  - Python 3.9+
  - requests (pip install requests)
  - GitHub token with:
      Issues: Read & Write
      Metadata: Read
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Dict, Iterator, Optional

import requests

API = "https://api.github.com"


def gh_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "bulk-unmerged-cleanup-script",
    }


def parse_link_header(link: Optional[str]) -> Dict[str, str]:
    if not link:
        return {}
    out: Dict[str, str] = {}
    for part in [p.strip() for p in link.split(",")]:
        segs = [s.strip() for s in part.split(";")]
        if len(segs) < 2:
            continue
        url = segs[0].strip("<> ")
        for s in segs[1:]:
            if s.startswith("rel="):
                out[s.split("=", 1)[1].strip('"')] = url
    return out


def request_with_rate_limit(
    session: requests.Session,
    method: str,
    url: str,
    headers: Dict[str, str],
    **kwargs,
) -> requests.Response:
    resp = session.request(method, url, headers=headers, **kwargs)

    if resp.status_code in (403, 429):
        remaining = resp.headers.get("X-RateLimit-Remaining")
        reset = resp.headers.get("X-RateLimit-Reset")
        retry_after = resp.headers.get("Retry-After")

        if remaining == "0" and reset:
            sleep_for = max(0, int(reset) - int(time.time()) + 2)
            print(f"[rate-limit] Sleeping {sleep_for}s", file=sys.stderr)
            time.sleep(sleep_for)
            resp = session.request(method, url, headers=headers, **kwargs)
        elif retry_after:
            sleep_for = int(retry_after) + 2
            print(f"[secondary rate-limit] Sleeping {sleep_for}s", file=sys.stderr)
            time.sleep(sleep_for)
            resp = session.request(method, url, headers=headers, **kwargs)

    return resp


def has_label(issue: dict, label_name: str) -> bool:
    return any(
        lbl.get("name", "").lower() == label_name.lower()
        for lbl in issue.get("labels", [])
    )


def iter_open_conflict_issues(
    session: requests.Session,
    owner: str,
    repo: str,
    headers: Dict[str, str],
    required_label: str = "conflict",
) -> Iterator[dict]:
    url = f"{API}/repos/{owner}/{repo}/issues"
    params = {"state": "open", "per_page": 100}

    while True:
        resp = request_with_rate_limit(session, "GET", url, headers, params=params)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to list issues: {resp.status_code} {resp.text}")

        for item in resp.json():
            if "pull_request" in item:
                continue
            if has_label(item, required_label):
                yield item

        links = parse_link_header(resp.headers.get("Link"))
        if "next" not in links:
            break
        url = links["next"]
        params = None


def ensure_label_exists(
    session: requests.Session,
    owner: str,
    repo: str,
    headers: Dict[str, str],
    label: str,
) -> None:
    get_url = f"{API}/repos/{owner}/{repo}/labels/{label}"
    resp = request_with_rate_limit(session, "GET", get_url, headers)
    if resp.status_code == 200:
        return
    if resp.status_code != 404:
        raise RuntimeError(resp.text)

    create_url = f"{API}/repos/{owner}/{repo}/labels"
    payload = {
        "name": label,
        "color": "B60205",
        "description": "Closed in bulk as unmerged",
    }
    resp = request_with_rate_limit(session, "POST", create_url, headers, json=payload)
    if resp.status_code != 201:
        raise RuntimeError(f"Failed to create label: {resp.text}")


def add_comment(
    session: requests.Session,
    owner: str,
    repo: str,
    number: int,
    headers: Dict[str, str],
    body: str,
) -> None:
    url = f"{API}/repos/{owner}/{repo}/issues/{number}/comments"
    resp = request_with_rate_limit(session, "POST", url, headers, json={"body": body})
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to comment on #{number}: {resp.text}")


def add_label(
    session: requests.Session,
    owner: str,
    repo: str,
    number: int,
    headers: Dict[str, str],
    label: str,
) -> None:
    url = f"{API}/repos/{owner}/{repo}/issues/{number}/labels"
    resp = request_with_rate_limit(session, "POST", url, headers, json={"labels": [label]})
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to label #{number}: {resp.text}")


def close_issue(
    session: requests.Session,
    owner: str,
    repo: str,
    number: int,
    headers: Dict[str, str],
) -> None:
    url = f"{API}/repos/{owner}/{repo}/issues/{number}"
    resp = request_with_rate_limit(session, "PATCH", url, headers, json={"state": "closed"})
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Failed to close #{number}: {resp.text}")


def lock_issue(
    session: requests.Session,
    owner: str,
    repo: str,
    number: int,
    headers: Dict[str, str],
) -> None:
    url = f"{API}/repos/{owner}/{repo}/issues/{number}/lock"
    resp = request_with_rate_limit(
        session, "PUT", url, headers, json={"lock_reason": "resolved"}
    )
    if resp.status_code != 204:
        raise RuntimeError(f"Failed to lock #{number}: {resp.text}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--owner", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--token", required=True)
    ap.add_argument("--required-label", default="conflict")
    ap.add_argument("--label", default="unmerged")
    ap.add_argument(
        "--comment",
        default=(
            "Closing this issue as part of a repository cleanup.\n\n"
            "This issue was not merged and is being archived for reference."
        ),
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--lock", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.2)
    ap.add_argument("--max", type=int, default=0)
    args = ap.parse_args()

    if not args.dry_run and not args.yes:
        print("Refusing to modify without --yes (or use --dry-run).", file=sys.stderr)
        return 2

    headers = gh_headers(args.token)

    with requests.Session() as session:
        if args.dry_run:
            print(f"[dry-run] Would ensure label '{args.label}' exists")
        else:
            ensure_label_exists(session, args.owner, args.repo, headers, args.label)

        issues = list(
            iter_open_conflict_issues(
                session,
                args.owner,
                args.repo,
                headers,
                required_label=args.required_label,
            )
        )
        if args.max:
            issues = issues[: args.max]

        print(f"Found {len(issues)} open issues with label '{args.required_label}'")

        for i, issue in enumerate(issues, 1):
            num = issue["number"]
            title = issue.get("title", "").strip()
            print(f"[{i}/{len(issues)}] #{num} {title}")

            if args.dry_run:
                print("  [dry-run] Would comment, label, close")
                continue

            add_comment(session, args.owner, args.repo, num, headers, args.comment)
            add_label(session, args.owner, args.repo, num, headers, args.label)
            close_issue(session, args.owner, args.repo, num, headers)
            if args.lock:
                lock_issue(session, args.owner, args.repo, num, headers)

            time.sleep(args.sleep)

        print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())