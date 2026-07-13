from application.services.integration.disambiguation.pairing import build_pairs
from application.services.integration.disambiguation.conflict_builder import build_full_conflict
from application.services.integration.disambiguation.prompts import build_prompt
from application.services.integration.disambiguation.proxy import decision_agreement_proxy
from application.services.integration.disambiguation.results import build_disambiguated_record, build_disambiguated_record_manual, build_no_conflict_record
from application.services.integration.disambiguation.issues import generate_github_body, generate_context, generate_conflict_file
from application.services.integration.disambiguation.utils import replace_with_full_entries, filter_relevant_fields, load_dict_from_jsonl, add_jsonl_record, load_pair_decisions, stable_hash, append_dict_to_jsonl
from infrastructure.config import PipelineConfig

import json
import logging
import os
import copy


from datetime import datetime, timezone



def log_error(conflict, error_conflicts_path=None):
    error_conflicts_path = error_conflicts_path or PipelineConfig().error_conflicts_path
    with open(error_conflicts_path, 'a') as f:
        f.write(json.dumps(conflict, indent=4))


def log_result(result, results_json_path=None):
    results_json_path = results_json_path or PipelineConfig().results_json_path
    with open(results_json_path, 'a') as f:
        f.write(json.dumps(result, indent=4))
    logging.info("Result logged")


def write_to_results_file(result, results_file):
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, "a") as f:
            json.dump(result, f)
            f.write("\n")
    except Exception as e:
        logging.error(f"Error writing to results file: {e}")

def load_solved_conflict_keys(jsonl_path):
    solved_keys = set()
    if not os.path.exists(jsonl_path):
        return solved_keys
    with open(jsonl_path, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    entry = json.loads(line)
                    key = next(iter(entry))
                    solved_keys.add(key)
                except Exception as e:
                    logging.warning(f"Could not parse line: {line[:100]}...\n{e}")
    return solved_keys




def build_record_from_legacy():
    "Buils the record to put in disambiguted_blocks if this disambiguation was already done"
    pass 

async def process_conflict(conflict_name, conflict, run_id, best_pair, pair_wise_decisions_path, clients, repos, dry_run=False):
    """
    Process a single conflict block: build pairs, disambiguate them, and return
    a disambiguated_blocks record for this block.

    Current conservative behavior:
    - process all pairs in the block
    - reuse cached pair decisions when available
    - ask the proxy for unresolved pairs
    - cache non-disagreement proxy decisions
    - create manual-review issues for disagreements
    - if any disagreement occurs, return block-level manual_review_pending
      after processing all pairs
    - otherwise return the normal disambiguated record
    """

    conflict_full = replace_with_full_entries(conflict, repos.pretools)

    conflict_pairs, _ = build_pairs(
        copy.deepcopy(conflict_full),
        conflict_name,
        more_than_two_pairs=0
    )

    pair_results = []
    n = 0

    manual_review_needed = False
    first_issue_url = None
    dry_run_first_manual_record = None

    for conflict_pair in conflict_pairs:
        n += 1
        pair_stable_id = f"p:{conflict_name.split('/')[0]}_{stable_hash(conflict_pair)}"

        # 1) Reuse cached pair decision
        if pair_stable_id in best_pair:
            decision = best_pair[pair_stable_id]

            pair_results.append({
                "remaining_id": conflict_pair["remaining"][0]["_id"],
                "disconnected_id": conflict_pair["disconnected"][0]["_id"],
                "same_as_remaining": decision.get("same_as_remaining"),
                "decision": decision.get("decision"),  # important for human unclear
                "confidence": decision.get("confidence"),
                "conflict_id": pair_stable_id,
                "source": decision.get("source"),
                "ts": decision.get("ts"),
            })
            continue

        # 2) Build enriched pair and run proxy
        full_conflict = filter_relevant_fields(conflict_pair, repos.publications)
        full_conflict = await build_full_conflict(full_conflict, clients)

        messages = build_prompt(
            full_conflict["disconnected"],
            full_conflict["remaining"],
            repos.publications,
        )
        result = decision_agreement_proxy(messages, clients)

        add_jsonl_record(str(PipelineConfig().proxy_results_path), {conflict_name: result})

        # 3) Proxy reached a decision
        if result.get("verdict") != "disagreement":
            now_ts = datetime.now(timezone.utc).isoformat()
            same_as_remaining = result["verdict"].lower() == "same"
            llm_decision = "same" if same_as_remaining else "different" 

            payload = {
                "pair_id": pair_stable_id,
                "kind": "pair",
                "decision": llm_decision,
                "same_as_remaining": same_as_remaining,
                "confidence": result.get("confidence", ""),
                "source": "llm",
                "ts": now_ts,
            }
            append_dict_to_jsonl(pair_wise_decisions_path, payload)

            # Keep in-memory cache updated during this run too
            best_pair[pair_stable_id] = payload
            

            pair_results.append({
                "remaining_id": conflict_pair["remaining"][0]["_id"],
                "disconnected_id": conflict_pair["disconnected"][0]["_id"],
                "same_as_remaining": same_as_remaining,
                "decision": llm_decision,
                "confidence": result.get("confidence"),
                "conflict_id": pair_stable_id,
                "source": "llm",
                "ts": now_ts,
            })
            continue

        # 4) Proxy disagreement -> manual review needed
        manual_review_needed = True

        if dry_run:
            print(f"[DRY-RUN] Would create GitHub issue for {conflict_name} ({pair_stable_id})")

            if dry_run_first_manual_record is None:
                dry_run_first_manual_record = {
                    "block_id": conflict_name,
                    "remaining": conflict.get("remaining"),
                    "disconnected": conflict.get("disconnected"),
                    "resolution": "manual_review_pending",
                    "issue_url": None,
                    "dry_run": True,
                    "would_create_issue": True,
                    "would_create_conflict_file": True,
                    "pair_id": pair_stable_id,
                    "pair_number": n,
                    "issue_title": f"Manual resolution needed for {conflict_name}_pair_{n}",
                }

            continue

        content, filename = generate_conflict_file(
            conflict_pair,
            conflict_name,
            pair_stable_id,
            run_id
        )
        path = f"{PipelineConfig().conflicts_repo_dir}/{filename}"
        conflict_url = clients.github.commit_file(content, path)

        context = generate_context(
            conflict_name,
            pair_stable_id,
            full_conflict,
            conflict_url,
            run_id
        )
        body = generate_github_body(context)

        title = f"Manual resolution needed for {conflict_name}_pair_{n}"
        labels = ["conflict", "automated"]
        response = clients.github.create_issue(title, body, labels)

        print(f"GitHub issue created for {conflict_name}, pair {n}")

        if first_issue_url is None:
            first_issue_url = response["html_url"]

    # Final decision after all pairs were processed
    if manual_review_needed:
        if dry_run:
            return dry_run_first_manual_record
        return build_disambiguated_record_manual(
            conflict_name,
            conflict,
            first_issue_url
        )

    return build_disambiguated_record(conflict_name, conflict, pair_results)

async def disambiguate_blocks(
    conflict_blocks,
    blocks,
    disambiguated_blocks_path,
    pair_wise_decisions_path,
    run_id,
    clients,
    repos,
    dry_run=False,
):
    """
    Disambiguate all blocks.

    In normal mode:
    - writes new records to disambiguated_blocks_path
    - creates conflict files / GitHub issues when needed

    In dry-run mode:
    - does NOT create conflict files / GitHub issues
    - does NOT write dry-run manual-review records to disambiguated_blocks_path
    - prints a summary of how many issues would be created and which pair_ids
      are involved
    """
    disambiguated_blocks = load_dict_from_jsonl(disambiguated_blocks_path)

    # best_pair maps each pair_key to the single highest-priority decision
    # (human > LLM, otherwise most informed / recent).
    best_pair = load_pair_decisions(pair_wise_decisions_path)

    n = 0
    errors_n = 0
    errors = []

    # Collect dry-run manual-review candidates here
    dry_run_issue_candidates = []

    for key in blocks:
        n += 1
        if n % 5000 == 0:
            print(f"Processed {n} blocks.")

        if key not in disambiguated_blocks:
            record = {}

            if key in conflict_blocks:
                # key is a conflict block
                try:
                    record = await process_conflict(
                        key,
                        conflict_blocks[key],
                        run_id,
                        best_pair,
                        pair_wise_decisions_path,
                        clients,
                        repos,
                        dry_run=dry_run,
                    )

                    # In dry-run mode, collect manual-review candidates for summary.
                    if dry_run and record and record.get("would_create_issue"):
                        dry_run_issue_candidates.append(record)

                    # Keep in-memory update only for normal mode,
                    # or for dry-run records that are not manual-review candidates.
                    if record and not (dry_run and record.get("would_create_issue")):
                        disambiguated_blocks.update(record)

                except Exception as e:
                    errors_n += 1
                    errors.append(key)
                    print(f"Error processing conflict {key}")
                    logging.error(f"Error processing conflict {key}: {e}")

            else:
                # key is not a conflict block
                record = build_no_conflict_record(key, blocks[key])

                # In dry-run mode there is no harm in keeping normal non-conflict records in memory
                disambiguated_blocks.update(record)

            # Write to file only in normal mode
            if record:
                add_jsonl_record(disambiguated_blocks_path, record)

        else:
            # Record already exists in disambiguated blocks, skipping
            pass

    print('#---------------- After first round ---------------------------------#')
    print(f"{errors_n} errors in first round of disambiguation")

    if errors_n:
        print("Examples of error blocks:")
        for item in errors:
            print(item)

    # ---------------- DRY-RUN SUMMARY ----------------
    if dry_run:
        print('#---------------- Dry-run summary -----------------------------------#')
        print(f"Would create {len(dry_run_issue_candidates)} GitHub issues / conflict files")

        if dry_run_issue_candidates:
            print("Pair IDs involved:")
            for item in dry_run_issue_candidates:
                print(f"- {item['pair_id']}  ({item['issue_title']})")

    return disambiguated_blocks