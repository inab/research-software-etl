"""
Stage-ordering guards for the full pipeline.

`license-normalization` rewrites `data.license` in the live `tools` collection,
which merge rebuilds from `pretools` every run. Normalizing before merge only
sanitized the previous run's tools, so the stage must run *after* merge. These
tests pin that ordering and the derived `--from-stage/--until` semantics, which
key off STAGES.index().
"""

from adapters.cli.pipeline_full import STAGES, _resolve_selected_stages


def test_license_normalization_runs_after_merge():
    assert STAGES.index("license-normalization") > STAGES.index("merge")


def test_license_normalization_runs_before_fairsoft():
    # FAIR scoring reads the license field, so normalization must precede it.
    assert STAGES.index("license-normalization") < STAGES.index("fairsoft")


def test_from_stage_license_normalization_starts_at_the_post_merge_point():
    selected = _resolve_selected_stages(from_stage="license-normalization")
    # The reorder means --from-stage=license-normalization no longer replays the
    # early stages; it starts at normalization and runs to the end.
    assert selected[0] == "license-normalization"
    assert "merge" not in selected
    assert selected[-1] == STAGES[-1]


def test_until_merge_excludes_license_normalization():
    selected = _resolve_selected_stages(until_stage="merge")
    assert "license-normalization" not in selected
    assert selected[-1] == "merge"


def test_skipping_merge_leaves_license_normalization_selectable():
    # license-normalization is not coupled to merge the way reindex is.
    selected = _resolve_selected_stages(do_merge_to_db=False)
    assert "merge" not in selected
    assert "reindex" not in selected
    assert "license-normalization" in selected
