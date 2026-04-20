from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_group_index(report: dict) -> dict[tuple[str, str], dict]:
    """
    Index suspicious group findings by (repo, group_id).
    """
    index = {}

    for item in report.get("suspicious_groups", []):
        repo = item.get("repo")
        group_id = item.get("group_id")
        if repo and group_id:
            index[(repo, group_id)] = item

    return index


def summarize_repo_candidates(report: dict) -> list[dict]:
    """
    Build a richer summary for each blacklist candidate repo.
    """
    group_index = build_group_index(report)
    summaries = []

    for candidate in report.get("blacklist_candidates", []):
        repo = candidate["repo"]
        group_examples = candidate.get("group_examples", [])

        all_names = set()
        per_group_name_counts = []
        per_group_names = []

        for example in group_examples:
            group_id = example.get("group_id")
            finding = group_index.get((repo, group_id))

            if finding:
                names = sorted(set(finding.get("distinct_names_in_group", [])))
            else:
                names = sorted(set(example.get("names", [])))

            all_names.update(names)
            per_group_name_counts.append(len(names))
            per_group_names.append(
                {
                    "group_id": group_id,
                    "unique_name_count": len(names),
                    "names": names,
                }
            )

        distribution_counter = Counter(per_group_name_counts)

        summaries.append(
            {
                "repo": repo,
                "score": candidate.get("score"),
                "group_count": candidate.get("group_count", 0),
                "instance_count": candidate.get("instance_count", 0),
                "pattern_hint": candidate.get("pattern_hint", False),
                "total_unique_names_affected": len(all_names),
                "all_unique_names_affected": sorted(all_names),
                "group_unique_name_count_distribution": dict(
                    sorted(distribution_counter.items())
                ),
                "max_unique_names_in_one_group": (
                    max(per_group_name_counts) if per_group_name_counts else 0
                ),
                "avg_unique_names_per_group": (
                    round(sum(per_group_name_counts) / len(per_group_name_counts), 2)
                    if per_group_name_counts
                    else 0
                ),
                "groups": per_group_names,
            }
        )

    summaries.sort(
        key=lambda x: (
            x["total_unique_names_affected"],
            x["max_unique_names_in_one_group"],
            x["group_count"],
            x["instance_count"],
        ),
        reverse=True,
    )

    return summaries


def compute_global_summary(report: dict, repo_summaries: list[dict]) -> dict:
    """
    Compute dataset-level summary statistics.

    Important distinction:
    - global_unique_names_affected_count:
        union of all unique names across all flagged repos
    - sum_repo_unique_names_affected:
        sum of per-repo counts (double-counts names that appear under multiple repos)

    The first is the best estimate of different tool identities affected.
    The second is useful as an upper-bound / burden measure.
    """
    suspicious_groups = report.get("suspicious_groups", [])

    global_unique_names = set()
    group_name_count_distribution = Counter()

    for group in suspicious_groups:
        names = set(group.get("distinct_names_in_group", []))
        global_unique_names.update(names)
        group_name_count_distribution[len(names)] += 1

    sum_repo_unique_names_affected = sum(
        item["total_unique_names_affected"] for item in repo_summaries
    )

    return {
        "repo_count": len(repo_summaries),
        "suspicious_group_count": len(suspicious_groups),
        "global_unique_names_affected_count": len(global_unique_names),
        "global_unique_names_affected": sorted(global_unique_names),
        "sum_repo_unique_names_affected": sum_repo_unique_names_affected,
        "group_unique_name_count_distribution": dict(
            sorted(group_name_count_distribution.items())
        ),
    }


def save_plot(group_distribution: dict[int, int], output_path: str) -> None:
    """
    Save a bar plot for:
    x = number of unique names in a suspicious group
    y = number of suspicious groups with that many names
    """
    if not group_distribution:
        plt.figure(figsize=(8, 5))
        plt.title("Distribution of unique-name counts in suspicious groups")
        plt.xlabel("Unique names in suspicious group")
        plt.ylabel("Number of suspicious groups")
        plt.tight_layout()
        plt.savefig(output_path, dpi=200)
        plt.close()
        return

    x_values = sorted(group_distribution.keys())
    y_values = [group_distribution[x] for x in x_values]

    plt.figure(figsize=(10, 6))
    plt.bar(x_values, y_values)
    plt.title("Distribution of unique-name counts in suspicious groups")
    plt.xlabel("Unique names in suspicious group")
    plt.ylabel("Number of suspicious groups")
    plt.xticks(x_values)
    plt.tight_layout()
    plt.savefig(output_path, dpi=200)
    plt.close()


def save_json(path: str, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def print_top_20(repo_summaries: list[dict]) -> None:
    print("\nTop 20 repos by affected unique names:\n")

    for idx, item in enumerate(repo_summaries[:20], start=1):
        print(
            f"{idx:2d}. {item['repo']}\n"
            f"    total_unique_names_affected={item['total_unique_names_affected']}, "
            f"max_unique_names_in_one_group={item['max_unique_names_in_one_group']}, "
            f"group_count={item['group_count']}, "
            f"instance_count={item['instance_count']}, "
            f"score={item['score']}"
        )


def write_blacklist_from_threshold(
    repo_summaries: list[dict],
    output_path: str,
    min_unique_names: int,
) -> list[str]:
    """
    Write a blacklist with repos whose total_unique_names_affected is strictly
    greater than the given threshold.
    """
    selected = [
        item["repo"]
        for item in repo_summaries
        if item["total_unique_names_affected"] > min_unique_names
    ]

    with open(output_path, "w", encoding="utf-8") as f:
        for repo in selected:
            f.write(repo + "\n")

    return selected

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Summarize hub_repo_report.json with global counts, top repos, and plot."
    )
    parser.add_argument(
        "--report-json",
        required=True,
        help="Path to hub_repo_report.json",
    )
    parser.add_argument(
        "--output-json",
        default="hub_repo_summary.json",
        help="Output JSON summary path.",
    )
    parser.add_argument(
        "--plot-output",
        default="hub_repo_group_name_distribution.png",
        help="Output PNG plot path.",
    )
    parser.add_argument(
        "--blacklist-output",
        default="hub_repo_blacklist_over_3_names.txt",
        help="Output txt file with blacklisted repos.",
    )
    parser.add_argument(
        "--blacklist-threshold",
        type=int,
        default=3,
        help="Blacklist repos with total_unique_names_affected greater than this value.",
    )

    args = parser.parse_args()

    report = load_json(args.report_json)
    repo_summaries = summarize_repo_candidates(report)
    global_summary = compute_global_summary(report, repo_summaries)

    output = {
        "summary": global_summary,
        "top_20_repos": repo_summaries[:20],
        "repos": repo_summaries,
    }

    save_json(args.output_json, output)
    save_plot(
        group_distribution=global_summary["group_unique_name_count_distribution"],
        output_path=args.plot_output,
    )

    print("\nGlobal summary:\n")
    print(
        f"Suspicious repos: {global_summary['repo_count']}\n"
        f"Suspicious groups: {global_summary['suspicious_group_count']}\n"
        f"Global unique names affected (union): "
        f"{global_summary['global_unique_names_affected_count']}\n"
        f"Sum of per-repo unique names affected: "
        f"{global_summary['sum_repo_unique_names_affected']}"
    )

    print_top_20(repo_summaries)

    print(f"\nSaved JSON summary to: {args.output_json}")
    print(f"Saved plot to: {args.plot_output}")

    blacklisted_repos = write_blacklist_from_threshold(
        repo_summaries=repo_summaries,
        output_path=args.blacklist_output,
        min_unique_names=args.blacklist_threshold,
    )
    print(f"Blacklisted repos (> {args.blacklist_threshold} unique names): {len(blacklisted_repos)}")
    print(f"Saved blacklist to: {args.blacklist_output}")


if __name__ == "__main__":
    main()