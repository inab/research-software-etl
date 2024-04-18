from src.core.domain.services.transformation.bioconda_opeb import biocondaOPEBStandardizer
from src.core.domain.entities.software_instance.main import operating_systems, data_sources

from pydantic import HttpUrl


class TestBiocondaopebStandardizer:

    # Transforms a single tool into an instance correctly.
    def test_transform_single_tool(self, mocker):
        tool = {
            '_id': 'bioconda/abaenrichment/cmd/1.10.0',
            '@last_updated_at': "2024-02-28T17:06:34.219Z",
            '@updated_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer/-/commit/45aa662604db6427c289c97ac24cfba730b78f72',
            '@updated_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer/-/pipelines/120779',
            'data': {
                "_id" : 'ObjectId("63cfc650925efaf98e0bedfd")',
                "@id" : "https://openebench.bsc.es/monitor/tool/bioconda:abyss:1.5.2/cmd/www.bcgsc.ca",
                "@label" : "abyss",
                "@license" : "https://creativecommons.org/licenses/by/4.0/",
                "@nmsp" : "bioconda",
                "@source_url" : "https://openebench.bsc.es/monitor/tool/bioconda:abyss:1.5.2/cmd/www.bcgsc.ca",
                "@timestamp" : "2023-02-27T02:53:53.206652Z",
                "@type" : "cmd",
                "@version" : "1.5.2",
                "alt_ids" : [],
                "confidence" : "ultimate",
                "contacts" : [],
                "credits" : [],
                "description" : "Assembly By Short Sequences - a de novo, parallel, paired-end sequence assembler",
                "distributions" : {
                    "binaries" : [],
                    "binary_packages" : [
                        "https://anaconda.org/bioconda/abyss/1.5.2/download/linux-64/abyss-1.5.2-boost1.61_5.tar.bz2",
                        "https://anaconda.org/bioconda/abyss/1.5.2/download/osx-64/abyss-1.5.2-boost1.61_5.tar.bz2"
                    ],
                    "containers" : [],
                    "source_packages" : [],
                    "sourcecode" : [
                        "https://github.com/bcgsc/abyss/releases/download/1.5.2/abyss-1.5.2.tar.gz"
                    ],
                    "vm_images" : [],
                    "vre" : []
                },
                "homepage" : "http://www.bcgsc.ca/platform/bioinfo/software/abyss",
                "languages" : [],
                "license" : "GPL3",
                "name" : "abyss",
                "os" : [],
                "publications" : [
                    {
                        "doi" : "10.1101/gr.089532.108"
                    }
                ],
                "repositories" : [
                    "http://git.code.sf.net/p/amos/code"
                ],
                "tags" : [],
                "web" : {
                    "homepage" : "http://www.bcgsc.ca/platform/bioinfo/software/abyss"
                }
            },
            '@data_source': 'bioconda',
            '@created_at': "2024-02-28T16:57:08.057Z",
            '@created_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer/-/commit/e2b685b10889a328a0d038d4fca92f5306a20736',
            '@created_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer/-/pipelines/120778'
                    
        }

        generator = biocondaOPEBStandardizer()
        standardized_tools = generator.process_transformation(tool)

        assert len(standardized_tools) == 1
        
        instance = standardized_tools[0]
        assert instance.name == 'abyss'
        assert instance.type == 'cmd'
        assert instance.version == ['1.5.2']
        assert instance.source == [ data_sources.bioconda ]
        assert instance.label == ['abyss']
        assert instance.description == ['Assembly By Short Sequences - a de novo, parallel, paired-end sequence assembler.']
        assert instance.webpage == [HttpUrl('http://www.bcgsc.ca/platform/bioinfo/software/abyss')]
        assert [item.model_dump() for item in   instance.publication ] == [{
            'doi': '10.1101/gr.089532.108',
            'cit_count' : None, 
            'citations' : [], 
            'pmcid' : None, 
            'pmid' : None, 
            'title' : None, 
            'year' : None, 
            'ref_count' : None, 
            'refs' : []
        }]
        
        assert instance.download == [
                    HttpUrl("https://anaconda.org/bioconda/abyss/1.5.2/download/linux-64/abyss-1.5.2-boost1.61_5.tar.bz2"),
                    HttpUrl("https://anaconda.org/bioconda/abyss/1.5.2/download/osx-64/abyss-1.5.2-boost1.61_5.tar.bz2"),
                    HttpUrl("https://github.com/bcgsc/abyss/releases/download/1.5.2/abyss-1.5.2.tar.gz")
                    ]
        
        assert instance.source_code == [HttpUrl("https://github.com/bcgsc/abyss/releases/download/1.5.2/abyss-1.5.2.tar.gz")]
        
        assert [item.model_dump() for item in  instance.documentation ] == [
            {'type': 'installation_instructions', 'url': HttpUrl('https://bioconda.github.io/recipes/abyss/README.html'), 'content': None},
            {'type': 'general', 'url': HttpUrl('https://bioconda.github.io/recipes/abyss/README.html'), 'content': None}
        ]
        
        assert [item.model_dump() for item in  instance.license] == [{
                                                                        'name': 'GPL-3.0-only',
                                                                        'url': HttpUrl('https://spdx.org/licenses/GPL-3.0-only.html'),
                                                                    }]

        assert  [item.model_dump() for item in  instance.repository ] == [{
            'url': HttpUrl("http://git.code.sf.net/p/amos/code"),
            'kind': None,
            'source_hasAnonymousAccess': None,
            'source_isDownloadRegistered': None,
            'source_isFree': None,
            'source_isRepoAccessible': None     
        }]
        assert instance.operating_system == [operating_systems.Linux, operating_systems.macOS, operating_systems.Windows]


    # Transforms a single tool with most fileds empty into an instance correctly.
    def test_transform_empty_fields(self):
        tool = {
            '_id': 'bioconda/abaenrichment/cmd/1.10.0',
            '@last_updated_at': "2024-02-28T17:06:34.219Z",
            '@updated_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer/-/commit/45aa662604db6427c289c97ac24cfba730b78f72',
            '@updated_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer/-/pipelines/120779',
            'data': {
                "_id" : 'ObjectId("63cfc650925efaf98e0bedfd")',
                "@id" : "https://openebench.bsc.es/monitor/tool/bioconda:abyss:1.5.2/cmd/www.bcgsc.ca",
                "@data_source" : "bioconda",
                "@label" : "abyss",
                "@license" : "https://creativecommons.org/licenses/by/4.0/",
                "@nmsp" : "bioconda",
                "@source_url" : "https://openebench.bsc.es/monitor/tool/bioconda:abyss:1.5.2/cmd/www.bcgsc.ca",
                "@timestamp" : "2023-02-27T02:53:53.206652Z",
                "@type" : "cmd",
                "@version" : "1.5.2",
                "alt_ids" : [],
                "confidence" : "ultimate",
                "contacts" : [],
                "credits" : [],
                "description" : "",
                "distributions" : {
                    "binaries" : [],
                    "binary_packages" : [],
                    "containers" : [],
                    "source_packages" : [],
                    "sourcecode" : [],
                    "vm_images" : [],
                    "vre" : []
                },
                "homepage" : "",
                "languages" : [],
                "license" : "",
                "name" : "",
                "os" : [],
                "publications" : [],
                "repositories" : [],
                "tags" : [],
                "web" : {
                    "homepage" : ""
                }
            },
            '@data_source': 'bioconda',
            '@created_at': "2024-02-28T16:57:08.057Z",
            '@created_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer/-/commit/e2b685b10889a328a0d038d4fca92f5306a20736',
            '@created_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-tools-importer/-/pipelines/120778'
        }
        generator = biocondaOPEBStandardizer()
        standardized_tools = generator.process_transformation(tool)
        assert len(standardized_tools) == 1

        instance = standardized_tools[0]
        assert instance.name == 'abyss'
        assert instance.type == 'cmd'
        assert instance.version == ['1.5.2']
        assert instance.source == [ data_sources.bioconda ]
        assert instance.label == ['abyss']
        assert instance.description == []
        assert instance.webpage == []
        assert instance.publication == []
        assert instance.download == []
        assert instance.source_code == []
        assert instance.documentation == []
        assert instance.license == []
        assert instance.repository == []
        assert instance.operating_system == [operating_systems.Linux, operating_systems.macOS, operating_systems.Windows]

        
