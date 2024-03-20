from FAIRsoft.transformation.galaxy_config import toolshedToolsGenerator
from FAIRsoft.classes.main import software_types, operating_systems
from pydantic import HttpUrl
import json

class TestGalaxyToolsGenerator:
    def test_transform_single_tool(self):
        tools = [
            {
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
            }
        ]

        generator = toolshedToolsGenerator(tools)

        assert len(generator.instSet.instances) == 1

        instance = generator.instSet.instances[0]
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

        tools = [
            {
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
            }
        ]

        generator = toolshedToolsGenerator(tools)
        assert len(generator.instSet.instances) == 1
