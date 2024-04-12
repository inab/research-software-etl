from src.core.domain.services.transformation.galaxy_metadata import galaxyMetadataToolsGenerator
from src.core.domain.entities.software_instance.main import software_types

class TestGalaxyMetadataToolsGenerator:
    def test_transform_single_tool(self):
        tools = [
            {
                '_id': 'galaxy_metadata/abslen_bed/cmd/1',
                '@last_updated_at': "2024-02-26T17:08:20.000Z",
                '@updated_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-metadata-importer/-/commit/00235a20431730b84ccf8bef17072e4b026eded0',
                '@updated_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-metadata-importer/-/pipelines/120234',
                '@created_at': "2024-02-26T17:08:20.000Z",
                '@created_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-metadata-importer/-/commit/00235a20431730b84ccf8bef17072e4b026eded0',
                '@created_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-metadata-importer/-/pipelines/120234',
                "data" : {
                    "_id" : 'ObjectId("6399e86e7f087e4dfcf210a3")',
                    "@id" : "https://openebench.bsc.es/monitor/tool/galaxy_metadata:predict_activity:1.0/cmd",
                    "@data_source" : "galaxy_metadata",
                    "dependencies" : [
                        "R/3.2.1",
                        "carettools/1.0"
                    ],
                    "id" : "predict_activity",
                    "name" : "Predict Activity",
                    "version" : "1.0"
                }
                
            }
        ]
    
        generator = galaxyMetadataToolsGenerator(tools)
        assert len(generator.instSet.instances) == 1

        instance = generator.instSet.instances[0]
        assert instance.name == "predict_activity"
        assert instance.type == software_types.cmd
        assert instance.version == ["1.0"]
        assert instance.source == ["galaxy_metadata"]
        assert instance.download == []
        assert instance.label == ["Predict Activity"]
        assert instance.dependencies == [
            "R/3.2.1",
            "carettools/1.0"
        ]

    def test_transform_tool_with_empty_fields_filled_correctly(self):
        tools = [            
            {
                '_id': 'galaxy_metadata/abslen_bed/cmd/1',
                '@last_updated_at': "2024-02-26T17:08:20.000Z",
                '@updated_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-metadata-importer/-/commit/00235a20431730b84ccf8bef17072e4b026eded0',
                '@updated_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-metadata-importer/-/pipelines/120234',
                '@created_at': "2024-02-26T17:08:20.000Z",
                '@created_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-metadata-importer/-/commit/00235a20431730b84ccf8bef17072e4b026eded0',
                '@created_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-metadata-importer/-/pipelines/120234',
                'data' : {
                    "_id" : 'ObjectId("6397235c7f087e4dfceecd75")',
                    "@id" : "https://openebench.bsc.es/monitor/tool/galaxy_metadata:a4:1.46.0/lib",
                    "@data_source" : "galaxy_metadata",
                    "dependencies" : [],
                    "id" : "predict_activity",
                    "name" : "Predict Activity",
                    "version" : "1.46.0"
                }
            }
        ]
    
        generator = galaxyMetadataToolsGenerator(tools)
        assert len(generator.instSet.instances) == 1

        instance = generator.instSet.instances[0]
        assert instance.name == "predict_activity"
        assert instance.type == software_types.cmd
        assert instance.version == ["1.46.0"]
        assert instance.source == ["galaxy_metadata"]
        assert instance.download == []
        assert instance.label == ["Predict Activity"]
        assert instance.dependencies == []
