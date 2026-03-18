from itertools import combinations
import json
def estimate_disambiguation_pairwise_from_conflicts(conflict_blocks):
    total_first_round = 0
    total_second_round = 0
    blocks_with_second_round = 0

    for block_id, conflict in conflict_blocks.items():
        disconnected = conflict.get("disconnected", [])
        n = len(disconnected)

        if n == 0:
            continue

        # First round: each disconnected vs merged remaining
        total_first_round += n

        # Second round: pairwise between disconnected entries
        if n > 1:
            second_round_pairs = n * (n - 1) // 2
            total_second_round += second_round_pairs
            blocks_with_second_round += 1

    return {
        "conflict_blocks_analyzed": len(conflict_blocks),
        "total_first_round_comparisons": total_first_round,
        "total_blocks_with_second_round": blocks_with_second_round,
        "total_second_round_comparisons": total_second_round,
        "total_estimated_comparisons": total_first_round + total_second_round
    }

if __name__ == "__main__":
    

    with open("scripts/data/disconnected_entries.json") as f:
        conflict_blocks = json.load(f)

    stats = estimate_disambiguation_pairwise_from_conflicts(conflict_blocks)

    for k, v in stats.items():
        print(f"{k}: {v}")