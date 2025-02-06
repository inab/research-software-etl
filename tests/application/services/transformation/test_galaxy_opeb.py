from src.application.services.transformation.galaxy_opeb import galaxyOPEBStandardizer
from src.domain.models.software_instance.main import software_types, data_sources
from pydantic import HttpUrl


class TestGalaxyopebStandardizer:

    # Transforms a single tool into an instance correctly.
    def test_transform_single_tool(self, mocker):
        tool = {
             '_id': 'galaxy/cometadapter/workflow/2.3.0',
            '@last_updated_at': "2024-02-28T17:09:49.300Z",
            '@updated_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer/-/commit/45aa662604db6427c289c97ac24cfba730b78f72',
            '@updated_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer/-/pipelines/120779',
            'data' : {
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
            },
            '@data_source': 'galaxy',
            '@created_at': "2024-02-28T16:59:18.863Z",
            '@created_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer/-/commit/e2b685b10889a328a0d038d4fca92f5306a20736',
            '@created_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer/-/pipelines/120778'
        }

        generator = galaxyOPEBStandardizer()
        standardized_tools = generator.process_transformation(tool)
        assert len(standardized_tools) == 1

        instance = standardized_tools[0]
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