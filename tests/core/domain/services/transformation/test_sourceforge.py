from src.core.domain.services.transformation.source_forge import sourceforgeToolsGenerator
from src.core.domain.entities.software_instance.main import operating_systems
from src.core.domain.entities.software_instance.repository import repository_kind
from pydantic import HttpUrl

class TestSourceForgeToolsGenerator:

    def test_transform_single_tool(self):
        tools = [
            {
                '_id': 'sourceforge/bio-bwa//',
                '@last_updated_at': "2024-02-29T13:07:34.066Z",
                '@updated_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/sourceforge-importer/-/commit/5e90d47d67e858c5fe9a5b64076f299f3869ebfa',
                '@updated_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/sourceforge-importer/-/pipelines/120914',
                'data' : {
                    "_id" : 'ObjectId("63cfb888925efaf98e0bcc92")',
                    "@id" : "https://openebench.bsc.es/monitor/tool/sourceforge:bio-bwa",
                    "@data_source" : "sourceforge",
                    "@source_url" : "https://sourceforge.net/projects/bio-bwa",
                    "description" : "BWA is a program for aligning sequencing reads against a large reference genome (e.g. human genome). It has two major components, one for read shorter than 150bp and the other for longer reads.",
                    "homepage" : "http://bio-bwa.sourceforge.net",
                    "last_update" : "2017-11-07",
                    "license" : [
                        "MIT License",
                        "GNU General Public License version 3.0 (GPLv3)"
                    ],
                    "name" : "bio-bwa",
                    "operating_systems" : [
                        "Linux",
                        "BSD"
                    ],
                    "registered" : False,
                    "repository" : "https://sourceforge.net/projects/bio-bwa"
                },
                '@data_source': 'sourceforge',
                '@source_url': 'https://sourceforge.net/projects/bio-bwa',
                '@created_at': "2024-02-29T11:40:02.381Z",
                '@created_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/sourceforge-importer/-/commit/5d162c5f1286efba9342d13b6f2bae7f7f2892ee',
                '@created_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/sourceforge-importer/-/pipelines/120893'
            }
        ]

        generator = sourceforgeToolsGenerator(tools)
        assert len(generator.instSet.instances) == 1

        instance = generator.instSet.instances[0]
        assert instance.name == "bio-bwa"
        assert instance.version == []
        assert instance.label == ["bio-bwa"]
        assert instance.source == ["sourceforge"]
        assert instance.operating_system == [operating_systems.Linux, operating_systems.BSD]
        assert instance.description == ["BWA is a program for aligning sequencing reads against a large reference genome (e.g. human genome). It has two major components, one for read shorter than 150bp and the other for longer reads."]
        assert [item.model_dump() for item in instance.license] == [
            {
                'name': 'MIT',
                'url': HttpUrl('https://spdx.org/licenses/MIT.html')
            },
            {
                'name': 'GPL-3.0-only',
                'url': HttpUrl('https://spdx.org/licenses/GPL-3.0-only.html')
            }
        ]
        assert [item.model_dump() for item in  instance.repository] == [
            {
                'kind': repository_kind.sourceforge,
                'url': HttpUrl('https://sourceforge.net/projects/bio-bwa'),
                'source_hasAnonymousAccess': None,
                'source_isDownloadRegistered': None,
                'source_isFree': None,
                'source_isRepoAccessible': None
            }
            ]
        assert instance.webpage == [HttpUrl('http://bio-bwa.sourceforge.net')]
    
    def test_transform_tool_with_empty_fields_filled_correctly(self):
        tools = [
            {
                '_id': 'sourceforge/bio-bwa//',
                '@last_updated_at': "2024-02-29T13:07:34.066Z",
                '@updated_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/sourceforge-importer/-/commit/5e90d47d67e858c5fe9a5b64076f299f3869ebfa',
                '@updated_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/sourceforge-importer/-/pipelines/120914',
                'data' : {
                    "_id" : 'ObjectId("63cfb888925efaf98e0bcc92")',
                    "@id" : "https://openebench.bsc.es/monitor/tool/sourceforge:bio-bwa",
                    "@data_source" : "sourceforge",
                    "@source_url" : "https://sourceforge.net/projects/bio-bwa",
                    "description" : None,
                    "homepage" : None,
                    "last_update" : None,
                    "license" : [],
                    "name" : "bio-bwa",
                    "operating_systems" : [],
                    "registered" : False,
                    "repository" : None
                },
                '@data_source': 'sourceforge',
                '@source_url': 'https://sourceforge.net/projects/bio-bwa',
                '@created_at': "2024-02-29T11:40:02.381Z",
                '@created_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/sourceforge-importer/-/commit/5d162c5f1286efba9342d13b6f2bae7f7f2892ee',
                '@created_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/sourceforge-importer/-/pipelines/120893'
            }
        ]

        generator = sourceforgeToolsGenerator(tools)
        assert len(generator.instSet.instances) == 1

        instance = generator.instSet.instances[0]
        assert instance.name == "bio-bwa"
        assert instance.version == []
        assert instance.label == ["bio-bwa"]
        assert instance.source == ["sourceforge"]
        assert instance.operating_system == []
        assert instance.description == []
        assert [item.model_dump() for item in instance.license] == []
        assert [item.model_dump() for item in  instance.repository] == [
            {
                'kind': repository_kind.sourceforge,
                'url': HttpUrl('https://sourceforge.net/projects/bio-bwa'),
                'source_hasAnonymousAccess': None,
                'source_isDownloadRegistered': None,
                'source_isFree': None,
                'source_isRepoAccessible': None
            }
            ]
        assert instance.webpage == []