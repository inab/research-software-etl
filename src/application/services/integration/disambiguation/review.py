"""Cache disambiguation decisions and escalate disagreements to curators.

`DisambiguationReviewService` owns the two non-LLM sides of disambiguation: the
pair-decision cache and GitHub issue creation. It knows nothing about the proxy.

The pair-decision cache (``config.pair_decisions_path``) is the curator decision
history and is deliberately **not** run-scoped -- it accumulates across runs.
"""

import logging
from datetime import datetime, timezone

from application.services.integration.disambiguation.issues import (
    generate_conflict_file,
    generate_context,
    generate_github_body,
)
from application.services.integration.disambiguation.utils import append_dict_to_jsonl

logger = logging.getLogger(__name__)


class DisambiguationReviewService:
    def __init__(self, clients, config, best_pair, run_id, dry_run=False):
        self.clients = clients
        self.config = config
        # Shared across the whole run: the caller passes the same dict for every
        # block, so recording a decision here updates the in-memory cache the next
        # block reads from.
        self.best_pair = best_pair
        self.run_id = run_id
        self.dry_run = dry_run

    def cached(self, pair_stable_id):
        """Return the best known decision for a pair, or None if unseen."""
        return self.best_pair.get(pair_stable_id)

    def record(self, pair_stable_id, result):
        """Persist a non-disagreement proxy verdict and update the in-memory cache.

        Returns the stored payload. Its ``confidence`` defaults to ``""`` (the
        proxy carries no top-level confidence on agreement); the orchestrator
        overrides it with the raw ``result`` value for the in-run pair result.
        """
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
        append_dict_to_jsonl(self.config.pair_decisions_path, payload)
        self.best_pair[pair_stable_id] = payload
        return payload

    def open_issue(self, conflict, conflict_pair, conflict_name, pair_stable_id, full_conflict, n):
        """Escalate a disagreement to a curator.

        Returns ``(issue_url, dry_run_record)``. In dry-run mode no GitHub call is
        made and ``(None, <record>)`` is returned so the orchestrator can surface
        the would-be issue; in normal mode the conflict file is committed, the
        issue is opened, and ``(url, None)`` is returned.
        """
        if self.dry_run:
            logger.info(
                "[DRY-RUN] Would create GitHub issue for %s (%s)",
                conflict_name,
                pair_stable_id,
            )
            dry_run_record = {
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
            return None, dry_run_record

        content, filename = generate_conflict_file(
            conflict_pair,
            conflict_name,
            pair_stable_id,
            self.run_id,
        )
        # A path inside the GitHub repository, committed through the API -- not a
        # write to the local checkout.
        path = f"{self.config.conflicts_repo_dir}/{filename}"
        conflict_url = self.clients.github.commit_file(content, path)

        context = generate_context(
            conflict_name,
            pair_stable_id,
            full_conflict,
            conflict_url,
            self.run_id,
        )
        body = generate_github_body(context, self.config.github_issue_template_path)

        title = f"Manual resolution needed for {conflict_name}_pair_{n}"
        labels = ["conflict", "automated"]
        response = self.clients.github.create_issue(title, body, labels)

        logger.info("GitHub issue created for %s, pair %s", conflict_name, n)
        return response["html_url"], None
