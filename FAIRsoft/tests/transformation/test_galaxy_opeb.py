from FAIRsoft.transformation.galaxy_opeb import galaxyOPEBToolsGenerator
from FAIRsoft.classes.main import software_types, operating_systems, data_sources
from FAIRsoft.classes.recognition import type_contributor
from FAIRsoft.classes.repository import repository_kind
from pydantic import HttpUrl
import pytest


class TestGalaxyopebtoolsgenerator:

    # Transforms a single tool into an instance correctly.
    def test_transform_single_tool(self, mocker):
        tools = [{
            "_id" : 'ObjectId("63cfc65b925efaf98e0bfa4b")',
            "@id" : "https://openebench.bsc.es/monitor/tool/galaxy:augustus:3.2.3/workflow/toolshed.g2.bx.psu.edu",
            "@data_source" : "galaxy",
            "@label" : "augustus",
            "@license" : "https://creativecommons.org/licenses/by/4.0/",
            "@nmsp" : "galaxy",
            "@source_url" : "https://openebench.bsc.es/monitor/tool/galaxy:augustus:3.2.3/workflow/toolshed.g2.bx.psu.edu",
            "@timestamp" : "2018-06-26T00:01:15.106Z",
            "@type" : "workflow",
            "@version" : "3.2.3",
            "alt_ids" : [

            ],
            "contacts" : [

            ],
            "credits" : [

            ],
            "description" : "gene prediction for prokaryotic and eukaryotic genomes",
            "name" : "augustus",
            "publications" : [

            ],
            "repositories" : [

            ],
            "web" : {
                "homepage" : "https://galaxy.bi.uni-freiburg.de/tool_runner?tool_id=toolshed.g2.bx.psu.edu%2Frepos%2Fbgruening%2Faugustus%2Faugustus%2F3.2.3"
            }
        }]

        generator = galaxyOPEBToolsGenerator(tools)
        assert len(generator.instSet.instances) == 1

        instance = generator.instSet.instances[0]
        assert instance.name == 'augustus'
        assert instance.type == software_types.cmd
        assert instance.version == ['3.2.3']
        assert instance.source == [data_sources.galaxy]
        assert instance.label == ['augustus']
        assert instance.description == ['Gene prediction for prokaryotic and eukaryotic genomes.']
        assert instance.publication == []
        assert instance.download == []
        assert instance.source_code == []
        assert instance.documentation == []
        assert instance.license == []
        assert instance.repository == []
        assert instance.webpage == [HttpUrl('https://galaxy.bi.uni-freiburg.de/tool_runner?tool_id=toolshed.g2.bx.psu.edu%2Frepos%2Fbgruening%2Faugustus%2Faugustus%2F3.2.3')]