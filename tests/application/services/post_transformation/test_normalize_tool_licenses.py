"""
License normalization against SPDX. Untestable before -- the SPDX lookup went
straight through the mongo singleton to a hardcoded `licensesMapping`.
"""

import pytest

from adapters.cli.post_transformation.normalize_licenses import update_tool_licenses
from application.services.post_transformation.normalize_tool_licenses import (
    normalize_tool_licenses,
)
from tests.fakes import FakeDatabaseAdapter, fake_repos

SPDX = [
    {
        "_id": "MIT",
        "licenseId": "MIT",
        "name": "MIT License",
        "synonyms": ["MIT license", "Expat"],
        "reference": "https://spdx.org/licenses/MIT.html",
        "isDeprecatedLicenseId": False,
    },
    {
        "_id": "GPL-2.0-only",
        "licenseId": "GPL-2.0-only",
        "name": "GNU General Public License v2.0 only",
        "synonyms": ["GPLv2"],
        "reference": "https://spdx.org/licenses/GPL-2.0-only.html",
        "isDeprecatedLicenseId": False,
    },
    {
        "_id": "GPL-2.0",
        "licenseId": "GPL-2.0",
        "name": "GNU General Public License v2.0",
        "synonyms": [],
        "reference": "https://spdx.org/licenses/GPL-2.0.html",
        "isDeprecatedLicenseId": True,
    },
]


@pytest.fixture
def db():
    return FakeDatabaseAdapter({"licenses": SPDX})


@pytest.fixture
def license_mapping(db):
    return fake_repos(db, license_mapping=True).license_mapping


def _tool(licenses):
    return {"_id": "t1", "data": {"name": "x", "license": licenses}}


def test_a_synonym_maps_to_the_spdx_identifier(license_mapping):
    result = normalize_tool_licenses(_tool([{"name": "Expat"}]), license_mapping)

    assert result == [{"name": "MIT", "url": "https://spdx.org/licenses/MIT.html"}]


def test_the_full_name_maps_too(license_mapping):
    result = normalize_tool_licenses(_tool([{"name": "GPLv2"}]), license_mapping)

    assert result == [
        {"name": "GPL-2.0-only", "url": "https://spdx.org/licenses/GPL-2.0-only.html"}
    ]


def test_a_deprecated_identifier_never_matches(license_mapping):
    """GPL-2.0 is in the mapping but deprecated, so it must pass through unmapped."""
    result = normalize_tool_licenses(_tool([{"name": "GPL-2.0"}]), license_mapping)

    assert result == [{"name": "GPL-2.0", "url": None}]


def test_an_unknown_license_is_kept_as_is(license_mapping):
    result = normalize_tool_licenses(_tool([{"name": "Weird Custom License"}]), license_mapping)

    assert result == [{"name": "Weird Custom License", "url": None}]


def test_licenses_that_collapse_to_the_same_spdx_id_are_deduplicated(license_mapping):
    result = normalize_tool_licenses(
        _tool([{"name": "Expat"}, {"name": "MIT license"}, {"name": "MIT"}]),
        license_mapping,
    )

    assert result == [{"name": "MIT", "url": "https://spdx.org/licenses/MIT.html"}]


def test_nameless_licenses_are_dropped(license_mapping):
    result = normalize_tool_licenses(_tool([{"name": ""}, {"url": "http://x"}]), license_mapping)

    assert result == []


def test_update_tool_licenses_writes_back_only_what_changed(db):
    db.insert_one("tools", {"_id": "t1", "data": {"license": [{"name": "Expat"}]}})
    db.insert_one(
        "tools",
        {
            "_id": "t2",
            "data": {"license": [{"name": "MIT", "url": "https://spdx.org/licenses/MIT.html"}]},
        },
    )
    repos = fake_repos(db, tools=True, license_mapping=True)

    summary = update_tool_licenses(repos)

    assert summary["total"] == 2
    assert summary["updated"] == 1, "t1 needed mapping"
    assert summary["unchanged"] == 1, "t2 was already normalized"
    assert summary["errors"] == 0

    assert repos.tools.get_all()[0]["data"]["license"] == [
        {"name": "MIT", "url": "https://spdx.org/licenses/MIT.html"}
    ]
