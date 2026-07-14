"""
The dependency arrow points inward: application/ and domain/ may not reach for
infrastructure. A module that imports the mongo singleton cannot be pointed at a
different collection and cannot be tested without a live database.

There is no longer a singleton to import -- the whole pipeline takes a
`Repositories` bundle -- so the rule below is now simply "nobody, ever". The
allowlist this test used to carry is empty and gone; if a new module reaches for
a database on its own, the check fails rather than growing a new exemption.
"""

from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"


def _modules_matching(needle: str) -> set[str]:
    offenders = set()
    for layer in ("application", "domain"):
        for path in (SRC / layer).rglob("*.py"):
            if needle in path.read_text():
                offenders.add(str(path.relative_to(SRC)))
    return offenders


def test_the_mongo_singleton_is_gone():
    """It was deleted, not merely unused: it cannot come back by import."""
    assert not (SRC / "infrastructure/db/mongo/mongo_db_singleton.py").exists()


def test_no_module_reaches_for_a_database_of_its_own():
    offenders = _modules_matching("mongo_db_singleton") | _modules_matching(
        "MongoDBAdapter("
    )

    assert not offenders, (
        "these modules build or import a database themselves; take a Repositories "
        f"argument instead (see infrastructure/db/repositories.py): {sorted(offenders)}"
    )


def test_no_module_below_adapters_reads_the_environment():
    """
    Config is read once, at the CLI, and passed down. os.getenv below adapters/
    means a stage's behaviour depends on something the run manifest never saw.
    """
    offenders = _modules_matching("os.getenv") | _modules_matching("os.environ")

    assert not offenders, (
        "these modules read the environment; add a field to PipelineConfig and "
        f"pass it down from the CLI instead: {sorted(offenders)}"
    )


def test_no_driver_types_leak_into_the_application_layer():
    """
    `pymongo.UpdateOne` used to be built in the web-availability use cases and handed
    to a raw `bulk_write`. Constructing driver objects is the repository's job: the
    application layer passes plain data.
    """
    offenders = set()
    for path in (SRC / "application").rglob("*.py"):
        if "from pymongo" in path.read_text() or "import pymongo" in path.read_text():
            offenders.add(str(path.relative_to(SRC)))

    assert not offenders, (
        "these modules import pymongo; move the query or the write into a repository "
        f"and pass plain dicts: {sorted(offenders)}"
    )
