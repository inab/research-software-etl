"""
Representative stats services over an in-memory database.

These sixteen services all do the same thing -- compute a document and append it
to the computations collection -- so a couple of them standing in for the shape is
enough. None had any coverage before: they imported the singleton, so there was
nowhere to put a fake.
"""

import pytest

from application.services.stats_generation.data.counts_source import count_tools
from application.services.stats_generation.data.type import count_types_tools
from application.services.stats_generation.trends.versioning import semantic_versioning
from tests.fakes import FakeDatabaseAdapter, fake_repos


def tool(name, type_="cmd", version=None, source="bioconda"):
    return {
        "_id": f"{source}/{name}",
        "data": {
            "name": name,
            "type": [type_],
            "version": [version] if version else [],
            "source": [source],
        },
    }


@pytest.fixture
def computations():
    return fake_repos(FakeDatabaseAdapter(), computations=True).computations


def test_count_types_tools_writes_one_document(computations):
    tools = [tool("a", "cmd"), tool("b", "cmd"), tool("c", "web")]

    count_types_tools(tools, "tools", computations)

    written = computations.find({"variable": "types_count"})
    assert len(written) == 1
    assert written[0]["data"] == {"cmd": 0.67, "web": 0.33}
    assert written[0]["collection"] == "tools"
    assert set(written[0]["createdFrom"]) == {t["_id"] for t in tools}


def test_count_tools_records_the_total(computations):
    count_tools([tool("a"), tool("b")], "eucaim", computations)

    written = computations.find({"variable": "tools_count"})
    assert len(written) == 1
    assert written[0]["collection"] == "eucaim"


def test_semantic_versioning_writes_a_document(computations):
    semantic_versioning([tool("a", version="1.0.0"), tool("b", version="nope")], "tools", computations)

    assert len(computations.find({})) == 1


def test_a_service_reaching_for_an_unwired_collection_raises():
    """fake_repos wires only what a test asks for, so a stray write fails loudly."""
    repos = fake_repos(FakeDatabaseAdapter(), tools=True)

    with pytest.raises(AttributeError):
        count_types_tools([tool("a")], "tools", repos.computations)
