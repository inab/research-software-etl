import logging

from application.services.integration.disambiguation.secondary_round import run_second_round
from application.services.integration.disambiguation.disambiguator import disambiguate_blocks
from application.services.integration.disambiguation.utils import load_dict_from_jsonl

logger = logging.getLogger(__name__)


async def run_full_disambiguation(config, run_id, clients, repos, dry_run):
    """
    Disambiguate every block, then keep re-running on the conflicts that remain.

    Every path comes from `config`, which the CLI built for this run -- inputs, the
    disambiguated-blocks output, the pair-decision cache and the proxy diagnostics
    alike. The services used to build a `PipelineConfig()` of their own, whose
    defaults are relative to the repository root, so a run wrote into the working
    tree rather than into its run directory.
    """

    # 1. Load input data

    blocks = load_dict_from_jsonl(config.grouped_json_path)
    conflict_blocks = load_dict_from_jsonl(config.conflicts_json_path)


    # 3. Run first round of disambiguation
    disambiguated_blocks = await disambiguate_blocks(
        conflict_blocks=conflict_blocks,
        blocks=blocks,
        config=config,
        run_id=run_id,
        clients=clients,
        repos=repos,
        dry_run=dry_run
    )


    unresolved_keys = [k for k in conflict_blocks if k not in disambiguated_blocks]

    logger.info("%s unresolved keys.", len(unresolved_keys))
    if len(unresolved_keys) > 0:
        logger.info("Unresolved keys: %s", ", ".join(unresolved_keys))

    # 4. Repeat second-round disambiguation until everything is resolved
    rounds_n = 0
    while len(unresolved_keys)>0 and rounds_n<5:
        rounds_n += 1
        # Run a second (or N-th) round
        disambiguated_blocks = await run_second_round(
            blocks=blocks,
            config=config,
            run_id=run_id,
            disambiguate_blocks_func=disambiguate_blocks,
            clients=clients,
            repos=repos,
            dry_run=dry_run
        )

        # Reload conflict_blocks to see what's left
        conflict_blocks = load_dict_from_jsonl(config.conflicts_json_path)

        unresolved_keys = [k for k in conflict_blocks if k not in disambiguated_blocks]

        if not unresolved_keys:
            logger.info("All conflicts resolved.")
            break
        else:
            logger.info("%s unresolved blocks remain. Continuing...", len(unresolved_keys))

    logger.info(
        "Disambiguation ended after %s second rounds; %s unresolved keys.",
        rounds_n,
        len(unresolved_keys),
    )
    if len(unresolved_keys) > 0:
        logger.info("Unresolved keys: %s", ", ".join(unresolved_keys))
