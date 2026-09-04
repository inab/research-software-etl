"""`transform_sources` must forward the incremental cutoff down to the raw
repository so only recently-updated entries are transformed."""

from datetime import datetime
from types import SimpleNamespace

from application.use_cases.transformation.main import transform_sources


class _CapturingRawRepo:
    """Records the (source, updated_since) it is asked for and yields nothing."""

    def __init__(self) -> None:
        self.calls = []

    def get_raw_documents_from_source(self, source, updated_since=None):
        self.calls.append((source, updated_since))
        return iter(())  # empty -> process_source returns after the first next()


def test_transform_sources_forwards_updated_since():
    raw = _CapturingRawRepo()
    repos = SimpleNamespace(alambique=raw)
    cutoff = datetime(2026, 8, 1)

    transform_sources(
        sources=["biotools", "github"], config=None, repos=repos, updated_since=cutoff
    )

    assert raw.calls == [("biotools", cutoff), ("github", cutoff)]


def test_transform_sources_defaults_to_no_filter():
    raw = _CapturingRawRepo()
    repos = SimpleNamespace(alambique=raw)

    transform_sources(sources=["biotools"], config=None, repos=repos)

    assert raw.calls == [("biotools", None)]
