"""
Use case: generate and persist FAIR scores for tools stored in MongoDB.

This module retrieves tool entries from the tools collection, computes their
individual FAIR scores, and stores the results in the computations collection.

Behavior:
- If `"tools"` is passed, all tools are processed; otherwise, tools are filtered by tag.
- For each tool, the use case recomputes and upserts the FAIR score only if the
  stored result is missing or outdated.
- If `force=True`, all matching tools are recomputed and upserted, even if the
  stored result is already up to date.

---> This module should be re-run every time the metadata collection is updated.
"""

from datetime import datetime

from application.services.stats_generation.FAIR.individual_scores import evaluate_tool
from domain.repositories import Repositories

VARIABLE = "FAIR_scores"


def utc_now_iso():
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def build_tools_query(tag_or_tools: str) -> dict:
    """
    tag_or_tools:
      - "tools" => all tools
      - otherwise => filter tools whose data.tags contains tag_or_tools
    """
    if tag_or_tools == "tools":
        return {}

    return {"data.tags": tag_or_tools}


def add_fair_scores(
    repos: Repositories,
    tag_or_tools: str = "tools",
    limit: int | None = None,
    force: bool = False,
):
    tools = repos.tools.find(build_tools_query(tag_or_tools))

    processed = 0
    skipped = 0
    failed = 0

    try:
        for entry in tools:
            entry_id = str(entry.get("_id"))
            tool_ts = entry.get("timestamp")

            if not entry_id or tool_ts is None:
                skipped += 1
                print(
                    f"[SKIP] Missing _id or timestamp: "
                    f"_id={entry.get('_id')} timestamp={tool_ts}"
                )
                continue

            # 1) Check if score exists and is up-to-date for this tool timestamp
            match = {
                "variable": VARIABLE,
                "createdFrom": [ entry_id ],
            }
            existing = repos.computations.find_one(match)

            if existing and existing.get("version") == tool_ts and not force:
                skipped += 1
                # Uncomment for verbose:
                # print(f"[SKIP] Up-to-date: {entry_id} @ {tool_ts}")
                continue

            # 2) Compute FAIR scores
            if force and existing and existing.get("version") == tool_ts:
                print(f"[FORCE] Recomputing up-to-date tool {entry_id} @ {tool_ts}")
            elif existing:
                print(f"[DO] Recomputing outdated tool {entry_id} @ {tool_ts}")
            else:
                print(f"[DO] Scoring new tool {entry_id} @ {tool_ts}")

            try:
                result = evaluate_tool(entry, repos.publications)

                doc = {
                    "variable": VARIABLE,
                    "createdFrom": [ entry_id ],
                    "version": tool_ts,  # tool record timestamp = "computed-for"
                    "createdAt": utc_now_iso(),  # computation time
                    "data": result,
                    "tags": entry.get("data", {}).get("tags", []),
                }

                # 3) Upsert: update if exists, else insert. This is why tool ids
                # must be stable across runs -- `match` is keyed on createdFrom.
                repos.computations.upsert(match, doc)

                processed += 1
                print(f"[OK] Stored FAIR scores for {entry_id}")

            except Exception as e:
                failed += 1
                print(f"[FAIL] {entry_id}: {type(e).__name__}: {e}")

            if limit is not None and processed >= limit:
                break

    except KeyboardInterrupt:
        print("\n[STOP] Interrupted (Ctrl+C). Safe to rerun; it will resume based on DB state.")

    print(
        f"\nDone. processed={processed}, "
        f"skipped={skipped}, failed={failed}, force={force}"
    )
