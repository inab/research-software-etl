from src.application.services.transformation.toolshed import toolshedStandardizer
from src.domain.models.software_instance.main import software_types, operating_systems
from pydantic import HttpUrl

class TestGalaxyStandardizer:
    def test_transform_single_tool(self):
        tool = {
                 '_id': 'galaxy_config/abritamr/cmd/1.0.14+galaxy1',
                '@last_updated_at': "2024-02-28T10:54:31.931Z",
                '@updated_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-config-importer/-/commit/4c1e763b18c9025a242cae7bc10e127634339a56',
                '@updated_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-config-importer/-/pipelines/120600',
                'data' : {
                    "_id" : 'ObjectId("63d15a21925efaf98e145ccb")',
                    "@id" : "https://openebench.bsc.es/monitor/tool/toolshed:10x_bamtofastq:1.4.1/cmd",
                    "@data_source" : "toolshed",
                    "@source_url" : "https://toolshed.g2.bx.psu.edu/repository/download?repository_id=783bde422b425bd9&changeset_revision=f71fd828c126&file_type=zip",
                    "citation" : [
                        {
                            "citation" : "\n            @misc{github10xbamtofastq,\n            author = {},\n            year = {2022},\n            title = {10x bamtofastq},\n            publisher = {Github},\n            journal = {Github repository},\n            url = {https://github.com/10XGenomics/bamtofastq},\n        }",
                            "type" : "bibtex"
                        }
                    ],
                    "code_file" : None,
                    "command" : "\n        bamtofastq --nthreads \"\\${GALAXY_SLOTS:-4}\" --reads-per-fastq 10000000000\n        #if $convert.reads == 'subset':\n            --locus $convert.locus\n        #end if\n        $produced_from\n        $tenx_bam\n        outdir &&\n        cd outdir; for i in */*.fastq.gz;do mv \\$i \\${i/\\//_};done\n    ",
                    "dataFormats" : {
                        "inputs" : [
                            "bam"
                        ],
                        "outputs" : [

                        ]
                    },
                    "description" : None,
                    "help" : "\n        10x Genomics BAM to FASTQ converter\n    ",
                    "id" : "10x_bamtofastq",
                    "interpreter" : None,
                    "language" : None,
                    "name" : "Convert a 10X BAM file to FASTQ",
                    "readme" : None,
                    "tests" : None,
                    "version" : "1.4.1"
                },
                '@repository_id': '8423143bf85371a0',
                '@changeset_revision': '3719342715a8',
                '@tool_path': 'abritamr-3719342715a8',
                '@data_source': 'toolshed',
                '@created_at': "2024-02-27T11:12:41.999Z",
                '@created_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-config-importer/-/commit/c11e263c834746332eec226bc8cc12f462df1e51',
                '@created_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-config-importer/-/pipelines/120412'         
            }

        generator = toolshedStandardizer()
        standardized_tools = generator.process_transformation(tool)
        
        assert len(standardized_tools) == 1

        instance = standardized_tools[0]
        with open('instance.json', 'w') as file:
            file.write(instance.model_dump_json())
        
        
        assert instance.name == "10x_bamtofastq"
        assert instance.type == software_types.cmd
        assert instance.version == ["1.4.1"]
        assert instance.source == ["toolshed"]
        assert instance.download == [HttpUrl("https://toolshed.g2.bx.psu.edu/repository/download?repository_id=783bde422b425bd9&changeset_revision=f71fd828c126&file_type=zip")]
        assert instance.label == ["Convert a 10X BAM file to FASTQ"]
        assert instance.description == []
        assert [item.model_dump() for item in instance.publication] == []
        assert [item.model_dump() for item in instance.documentation] == [{'type':'help', 'url': None, 'content': "\n        10x Genomics BAM to FASTQ converter\n    "}]
        assert set(instance.operating_system) == set([operating_systems.Linux, operating_systems.macOS])
        assert instance.test == False
        assert [item.model_dump() for item in instance.input] == [
            {
                'term': 'BAM',
                'uri': HttpUrl('http://edamontology.org/format_2572'),
                'vocabulary': 'EDAM',
                'datatype': None
            }
        ]
        assert [item.model_dump() for item in instance.output] == []
    
    def test_transform_tool_with_empty_fields_filled_correctly(self):
        '''
        The following metadata dictionary should not raise any errors. Differences with the previous test:
        - "dataFormats" field missing
        - "help" field empty
        - "citation" field empty
        - "description" field empty
        '''

        tool = {  
                '_id': 'galaxy_config/abritamr/cmd/1.0.14+galaxy1',
                '@last_updated_at': "2024-02-28T10:54:31.931Z",
                '@updated_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-config-importer/-/commit/4c1e763b18c9025a242cae7bc10e127634339a56',
                '@updated_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-config-importer/-/pipelines/120600',
                'data' : {
                    "_id" : 'ObjectId("63d15a21925efaf98e145ccb")',
                    "@id" : "https://openebench.bsc.es/monitor/tool/toolshed:10x_bamtofastq:1.4.1/cmd",
                    "@data_source" : "toolshed",
                    "@source_url" : "https://toolshed.g2.bx.psu.edu/repository/download?repository_id=783bde422b425bd9&changeset_revision=f71fd828c126&file_type=zip",
                    "citation" : [],
                    "code_file" : None,
                    "command" : "\n        bamtofastq --nthreads \"\\${GALAXY_SLOTS:-4}\" --reads-per-fastq 10000000000\n        #if $convert.reads == 'subset':\n            --locus $convert.locus\n        #end if\n        $produced_from\n        $tenx_bam\n        outdir &&\n        cd outdir; for i in */*.fastq.gz;do mv \\$i \\${i/\\//_};done\n    ",
                    "description" : None,
                    "help" : None,
                    "id" : "10x_bamtofastq",
                    "interpreter" : None,
                    "language" : None,
                    "name" : "Convert a 10X BAM file to FASTQ",
                    "readme" : None,
                    "tests" : None,
                    "version" : "1.4.1"
                    },
                '@repository_id': '8423143bf85371a0',
                '@changeset_revision': '3719342715a8',
                '@tool_path': 'abritamr-3719342715a8',
                '@data_source': 'toolshed',
                '@created_at': "2024-02-27T11:12:41.999Z",
                '@created_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-config-importer/-/commit/c11e263c834746332eec226bc8cc12f462df1e51',
                '@created_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/toolshed-config-importer/-/pipelines/120412'
            }
        

        generator = toolshedStandardizer()
        standardized_tools = generator.process_transformation(tool)
        assert len(standardized_tools) == 1
