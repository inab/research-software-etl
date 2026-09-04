"""
Regression tests for the null-license / null-citation hazard.

A single-source tool from `bioconda_recipes` (whose transformer returns None
when `about.license` is absent) used to carry `license: None` all the way into
the `tools` collection, where the observatory API's /initial-search iterates
`tool['license']` and crashes with `'NoneType' object is not iterable`. The
model must coerce None -> [] for both `license` and `citation`, and the `tools`
model (multitype_instance) inherits that coercion so merge cannot reintroduce
the null.
"""

from domain.models.software_instance.main import instance
from domain.models.software_instance.multitype_instance import multitype_instance


def _dump_licenses(model):
    return [lic.model_dump() for lic in model.license]


class TestLicenseCoercion:
    def test_none_license_becomes_empty_list(self):
        assert instance(name="x", license=None).license == []

    def test_omitted_license_defaults_to_empty_list(self):
        assert instance(name="x").license == []

    def test_two_instances_do_not_share_the_default_list(self):
        """default_factory=list must give each instance its own list."""
        a = instance(name="a")
        b = instance(name="b")
        a.license = [{"name": "MIT"}]
        assert b.license == []

    def test_items_with_neither_name_nor_url_are_dropped(self):
        model = instance(
            name="x",
            license=[{"name": "MIT"}, {"name": "", "url": None}, {}],
        )
        assert _dump_licenses(model) == [{"name": "MIT", "url": None}]

    def test_name_only_license_is_kept(self):
        model = instance(name="x", license=[{"name": "GPL-2.0"}])
        assert _dump_licenses(model) == [{"name": "GPL-2.0", "url": None}]


class TestCitationCoercion:
    def test_none_citation_becomes_empty_list(self):
        assert instance(name="x", citation=None).citation == []

    def test_omitted_citation_defaults_to_empty_list(self):
        assert instance(name="x").citation == []

    def test_citation_content_is_preserved(self):
        cites = [{"title": "A tool", "year": "2020"}]
        assert instance(name="x", citation=cites).citation == cites


class TestToolsModelInheritsCoercion:
    """multitype_instance is the schema written to the tools collection."""

    def test_merge_stage_construction_null_license_and_citation(self):
        # Mirrors convert_to_multi_type_instance: license/citation may be None
        # for a single-source bioconda_recipes entry.
        tool = multitype_instance(
            name="x",
            type=["cmd"],
            other_names=[],
            license=None,
            citation=None,
        )
        assert tool.license == []
        assert tool.citation == []

        dumped = tool.model_dump(mode="json")
        assert dumped["license"] == []
        assert dumped["citation"] == []
