from FAIRsoft.transformation.source_forge import sourceforgeToolsGenerator
from FAIRsoft.classes.main import software_types, operating_systems, data_sources
from FAIRsoft.classes.recognition import type_contributor
from FAIRsoft.classes.repository import repository_kind
from pydantic import HttpUrl
import pytest

class TestSourceForgeToolsGenerator:

    def test_transform_single_tool(self):
        tools = [
            {
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