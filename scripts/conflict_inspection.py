from itertools import combinations
import json
def analyze_name_divergence_in_blocks(grouped_entries):
    total_blocks = 0
    divergent_blocks = 0
    total_comparisons_needed = 0

    for group_key, group_data in grouped_entries.items():
        instances = group_data.get("instances", [])
        if len(instances) < 2:
            continue  # no ambiguity in single-entry groups

        total_blocks += 1

        # Extract unique normalized names
        names = {inst['data']['name'].strip().lower() for inst in instances if inst['data'].get('name')}
        if len(names) > 1:
            divergent_blocks += 1
            n = len(names)
            total_comparisons_needed += n * (n - 1) // 2

    return {
        "total_blocks": total_blocks,
        "divergent_blocks_with_different_names": divergent_blocks,
        "total_pairwise_comparisons_needed": total_comparisons_needed
    }

def analyze_bioconductor_name_cases(grouped_entries):
    total_blocks = 0
    divergent_blocks = 0
    bioconductor_alias_blocks = 0

    for group_key, group_data in grouped_entries.items():
        instances = group_data.get("instances", [])
        if len(instances) < 2:
            continue

        total_blocks += 1

        names = {inst['data']['name'].strip().lower() for inst in instances if inst['data'].get('name')}
        if len(names) > 1:
            divergent_blocks += 1

            # Check for the bioconductor-name pattern
            for name in names:
                bioc_name = f"bioconductor-{name}"
                if bioc_name in names:
                    bioconductor_alias_blocks += 1
                    break  # count this group once

    return {
        "total_blocks": total_blocks,
        "divergent_blocks_with_different_names": divergent_blocks,
        "bioconductor_alias_blocks": bioconductor_alias_blocks
    }

def estimate_pairwise_comparisons_excluding_bioconductor(grouped_entries):

    total_blocks = 0
    total_blocks_several_instances = 0
    divergent_blocks = 0
    divergent_blocks_excluding_bioc = 0
    total_comparisons_excluding_bioc = 0

    for group_key, group_data in grouped_entries.items():
        instances = group_data.get("instances", [])
        
        total_blocks += 1

        if len(instances) < 2:
            continue

        total_blocks_several_instances += 1

        names = {inst['data']['name'].strip().lower() for inst in instances if inst['data'].get('name')}
        if len(names) > 1:
            divergent_blocks += 1

            # Check if the only difference is bioconductor- prefix
            simple_alias = False
            for name in names:
                bioc_name = f"bioconductor-{name}"
                if bioc_name in names:
                    simple_alias = True
                    break

            if not simple_alias:
                divergent_blocks_excluding_bioc += 1
                n = len(names)
                total_comparisons_excluding_bioc += n * (n - 1) // 2

    return {
        "total_blocks": total_blocks,
        "total_blocks_several_instances": total_blocks_several_instances,
        "divergent_blocks_with_different_names": divergent_blocks,
        "divergent_blocks_excluding_bioconductor_cases": divergent_blocks_excluding_bioc,
        "total_pairwise_comparisons_needed_excluding_bioconductor": total_comparisons_excluding_bioc
    }


if __name__ == "__main__":
    # Load the cleaned grouped entries
    with open("scripts/data/grouped_entries_no_opeb.json", "r") as f:
        grouped_no_opeb = json.load(f)

    # Analyze them
    divergence_stats = analyze_name_divergence_in_blocks(grouped_no_opeb)

    for k, v in divergence_stats.items():
        print(f"{k}: {v}")

    print("\n" + "=" * 40 + "\n")
    
    # Analyze for bioconductor name patterns
    bioconductor_stats = analyze_bioconductor_name_cases(grouped_no_opeb)

    for k, v in bioconductor_stats.items():
        print(f"{k}: {v}")

    print("\n" + "=" * 40 + "\n")

    final_stats = estimate_pairwise_comparisons_excluding_bioconductor(grouped_no_opeb)

    for k, v in final_stats.items():
        print(f"{k}: {v}")