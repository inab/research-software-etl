"""
The mongo singleton is infrastructure. Nothing in application/ or domain/ should
see it: a module that imports it cannot be pointed at a different collection, and
cannot be tested without a live database.

Phase 1 took the core pipeline (transformation, grouping, merge, disambiguation,
license normalization) off it. The stats and web-availability stages are still on
it, and are listed below so this test pins the boundary rather than waiting for
the whole migration: the list may only ever shrink. When it empties, delete both
the list and mongo_db_singleton.py.
"""

from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"

STILL_ON_THE_SINGLETON = {
    "application/services/stats_generation/FAIR/fair_distribution.py",
    "application/services/stats_generation/FAIR/individual_scores.py",
    "application/services/stats_generation/data/counts_source.py",
    "application/services/stats_generation/data/coverage.py",
    "application/services/stats_generation/data/features.py",
    "application/services/stats_generation/data/metadata_completeness.py",
    "application/services/stats_generation/data/type.py",
    "application/services/stats_generation/trends/dependencies.py",
    "application/services/stats_generation/trends/documentation.py",
    "application/services/stats_generation/trends/formats.py",
    "application/services/stats_generation/trends/licenses.py",
    "application/services/stats_generation/trends/publications.py",
    "application/services/stats_generation/trends/version_control.py",
    "application/services/stats_generation/trends/versioning.py",
    "application/use_cases/stats/generate_fair_scores.py",
    "application/use_cases/stats/generate_similarity.py",
    "application/use_cases/stats/generate_stats.py",
    "application/use_cases/web_availability/tag_relevant_webavailability_urls.py",
    "application/use_cases/web_availability/update_web_availability_daily.py",
}


def _modules_importing_the_singleton() -> set[str]:
    offenders = set()
    for layer in ("application", "domain"):
        for path in (SRC / layer).rglob("*.py"):
            if "mongo_db_singleton" in path.read_text():
                offenders.add(str(path.relative_to(SRC)))
    return offenders


def test_no_new_module_reaches_for_the_mongo_singleton():
    offenders = _modules_importing_the_singleton()

    new = offenders - STILL_ON_THE_SINGLETON
    assert not new, (
        "these modules import the mongo singleton; take a Repositories bundle "
        f"as an argument instead (see infrastructure/db/repositories.py): {sorted(new)}"
    )


def test_the_allowlist_does_not_go_stale():
    offenders = _modules_importing_the_singleton()

    fixed = STILL_ON_THE_SINGLETON - offenders
    assert not fixed, (
        "these modules no longer import the singleton -- remove them from "
        f"STILL_ON_THE_SINGLETON so it cannot grow back: {sorted(fixed)}"
    )


def test_no_module_below_adapters_reads_the_environment():
    """
    Config is read once, at the CLI, and passed down. os.getenv below adapters/
    means a stage's behaviour depends on something the run manifest never saw.
    """
    offenders = set()
    for layer in ("application", "domain"):
        for path in (SRC / layer).rglob("*.py"):
            if "os.getenv" in path.read_text() or "os.environ" in path.read_text():
                offenders.add(str(path.relative_to(SRC)))

    assert not offenders, (
        "these modules read the environment; add a field to PipelineConfig and "
        f"pass it down from the CLI instead: {sorted(offenders)}"
    )
