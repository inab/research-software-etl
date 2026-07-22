"""Score conflict pairs with the LLM agreement proxy.

`PairScoringService` owns the LLM side of disambiguation: it turns a hydrated
conflict block into pairs and scores each pair via the agreement proxy. It knows
nothing about the pair-decision cache, GitHub, or the block-level bookkeeping --
those live in :class:`DisambiguationReviewService` and the orchestrator. Its only
write is the run-scoped proxy diagnostic, which already landed in the run
directory before the split (see the CLAUDE.md "stage must not write into the
working tree" note).
"""

import copy
import logging
from dataclasses import dataclass

from application.services.integration.disambiguation.pairing import build_pairs
from application.services.integration.disambiguation.conflict_builder import build_full_conflict
from application.services.integration.disambiguation.prompts import build_prompt
from application.services.integration.disambiguation.proxy import decision_agreement_proxy
from application.services.integration.disambiguation.utils import (
    filter_relevant_fields,
    add_jsonl_record,
)

logger = logging.getLogger(__name__)


@dataclass
class ScoredPair:
    """The proxy verdict for a pair, plus the enriched conflict it was scored on.

    ``full_conflict`` is carried through because the review service needs it to
    build the GitHub issue context on a disagreement -- recomputing it would mean
    a second round of link enrichment.
    """

    result: dict
    full_conflict: dict


class PairScoringService:
    def __init__(self, clients, repos, proxy_results_path):
        self.clients = clients
        self.repos = repos
        self.proxy_results_path = proxy_results_path

    def build_pairs(self, conflict_full, conflict_name):
        """Split a hydrated conflict block into the pairs to score."""
        pairs, _ = build_pairs(
            copy.deepcopy(conflict_full),
            conflict_name,
            more_than_two_pairs=0,
        )
        return pairs

    async def score(self, conflict_pair, conflict_name):
        """Score a single pair via the agreement proxy.

        Enriches the pair (link/repo content), builds the prompt, asks the proxy,
        and appends the raw verdict to the run's proxy-diagnostics file.
        """
        full_conflict = filter_relevant_fields(conflict_pair, self.repos.publications)
        full_conflict = await build_full_conflict(full_conflict, self.clients)

        messages = build_prompt(
            full_conflict["disconnected"],
            full_conflict["remaining"],
            self.repos.publications,
        )
        result = decision_agreement_proxy(messages, self.clients)

        add_jsonl_record(str(self.proxy_results_path), {conflict_name: result})

        return ScoredPair(result=result, full_conflict=full_conflict)
