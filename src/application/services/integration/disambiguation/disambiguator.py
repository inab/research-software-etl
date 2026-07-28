import logging

from application.services.integration.disambiguation.results import (
    build_disambiguated_record,
    build_disambiguated_record_manual,
    build_no_conflict_record,
)
from application.services.integration.disambiguation.pair_scoring import PairScoringService
from application.services.integration.disambiguation.review import DisambiguationReviewService
from application.services.integration.disambiguation.utils import (
    replace_with_full_entries,
    load_dict_from_jsonl,
    add_jsonl_record,
    load_pair_decisions,
    stable_hash,
)

logger = logging.getLogger(__name__)


def _pair_result_from_decision(conflict_pair, pair_stable_id, decision):
    """Shape a pair decision (cached or freshly scored) into a pair-result row."""
    return {
        "remaining_id": conflict_pair["remaining"][0]["_id"],
        "disconnected_id": conflict_pair["disconnected"][0]["_id"],
        "same_as_remaining": decision.get("same_as_remaining"),
        "decision": decision.get("decision"),  # important for human unclear
        "confidence": decision.get("confidence"),
        "conflict_id": pair_stable_id,
        "source": decision.get("source"),
        "ts": decision.get("ts"),
    }


async def process_conflict(conflict_name, conflict, run_id, best_pair, config, clients, repos, dry_run=False):
    """
    Process a single conflict block: build pairs, disambiguate them, and return
    a disambiguated_blocks record for this block.

    Orchestration only. Scoring (LLM) lives in `PairScoringService`; the
    pair-decision cache and GitHub issue creation live in
    `DisambiguationReviewService`. Every path comes from `config` -- the one the
    CLI built for this run.

    Per pair: reuse a cached decision, else score it; record non-disagreement
    verdicts; on a disagreement escalate to a curator. If any pair disagrees the
    block returns manual_review_pending after all pairs are processed; otherwise
    the normal disambiguated record.
    """
    scoring = PairScoringService(clients, repos, config.proxy_results_path)
    review = DisambiguationReviewService(clients, config, best_pair, run_id, dry_run=dry_run)

    conflict_full = replace_with_full_entries(conflict, repos.pretools)
    conflict_pairs = scoring.build_pairs(conflict_full, conflict_name)

    pair_results = []
    n = 0

    manual_review_needed = False
    first_issue_url = None
    dry_run_first_manual_record = None

    for conflict_pair in conflict_pairs:
        n += 1
        pair_stable_id = f"p:{conflict_name.split('/')[0]}_{stable_hash(conflict_pair)}"

        # 1) Reuse cached pair decision
        cached = review.cached(pair_stable_id)
        if cached is not None:
            pair_results.append(_pair_result_from_decision(conflict_pair, pair_stable_id, cached))
            continue

        # 2) Score the pair with the agreement proxy
        scored = await scoring.score(conflict_pair, conflict_name)

        # 3) Proxy reached a decision
        if scored.result.get("verdict") != "disagreement":
            payload = review.record(pair_stable_id, scored.result)
            # The persisted payload defaults confidence to ""; the in-run pair
            # result has historically used the raw proxy value (None when absent).
            decision = {**payload, "confidence": scored.result.get("confidence")}
            pair_results.append(_pair_result_from_decision(conflict_pair, pair_stable_id, decision))
            continue

        # 4) Proxy disagreement -> manual review needed
        manual_review_needed = True
        issue_url, dry_run_record = review.open_issue(
            conflict,
            conflict_pair,
            conflict_name,
            pair_stable_id,
            scored.full_conflict,
            n,
        )

        if dry_run:
            if dry_run_first_manual_record is None:
                dry_run_first_manual_record = dry_run_record
            continue

        if first_issue_url is None:
            first_issue_url = issue_url

    # Final decision after all pairs were processed
    if manual_review_needed:
        if dry_run:
            return dry_run_first_manual_record
        return build_disambiguated_record_manual(
            conflict_name,
            conflict,
            first_issue_url,
        )

    return build_disambiguated_record(conflict_name, conflict, pair_results)


async def disambiguate_blocks(
    conflict_blocks,
    blocks,
    config,
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
    - logs a summary of how many issues would be created and which pair_ids
      are involved
    """
    disambiguated_blocks_path = config.disambiguated_blocks_path
    disambiguated_blocks = load_dict_from_jsonl(disambiguated_blocks_path)

    # best_pair maps each pair_key to the single highest-priority decision
    # (human > LLM, otherwise most informed / recent).
    best_pair = load_pair_decisions(config.pair_decisions_path)

    n = 0
    errors_n = 0
    errors = []

    # Collect dry-run manual-review candidates here
    dry_run_issue_candidates = []

    for key in blocks:
        n += 1
        if n % 5000 == 0:
            logger.info("Processed %s blocks.", n)

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
                        config,
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
                    logger.error("Error processing conflict %s: %s", key, e)

            else:
                # key is not a conflict block
                record = build_no_conflict_record(key, blocks[key])

                # In dry-run mode there is no harm in keeping normal non-conflict records in memory
                disambiguated_blocks.update(record)

            # Persist the record, except a dry-run manual-review candidate: it is
            # a flat diagnostic dict (not `{conflict_id: {block}}`), so writing it
            # would corrupt the JSONL for downstream loaders. Same guard as the
            # in-memory update above; matches this function's dry-run docstring.
            if record and not (dry_run and record.get("would_create_issue")):
                add_jsonl_record(disambiguated_blocks_path, record)

        else:
            # Record already exists in disambiguated blocks, skipping
            pass

    logger.info("After first round: %s errors in first round of disambiguation", errors_n)

    if errors_n:
        logger.warning("Examples of error blocks: %s", ", ".join(errors))

    # ---------------- DRY-RUN SUMMARY ----------------
    if dry_run:
        logger.info(
            "Dry-run summary: would create %s GitHub issues / conflict files",
            len(dry_run_issue_candidates),
        )

        if dry_run_issue_candidates:
            logger.info(
                "Pair IDs involved: %s",
                ", ".join(
                    f"{item['pair_id']} ({item['issue_title']})"
                    for item in dry_run_issue_candidates
                ),
            )

    return disambiguated_blocks
