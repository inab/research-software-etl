'''
--------------------------------------------
                DEPRECATED
--------------------------------------------
New importer of repositories in the making.
'''

from src.core.domain.services.transformation.repository import repositoryToolsGenerator
from src.core.domain.entities.software_instance.main import software_types, data_sources
from src.core.domain.entities.software_instance.recognition import type_contributor
from src.core.domain.entities.software_instance.repository import repository_kind
from pydantic import HttpUrl
import pytest
class TestRepositoryToolsGenerator:

    def test_transform_single_tool(self):
        tools = [
           {
                "_id" : 'ObjectId("602a96dd651dd46a70b0836c")',
                "@id" : "https://openebench.bsc.es/monitor/tool/repository:n1pas/lib",
                "@data_source" : "repository",
                "entry_links" : [
                    "https://github.com/grizant/n1pas/tree/master"
                ],
                "repos" : [
                    {
                        "instance" : None,
                        "kind" : "github",
                        "links" : [
                            "https://github.com/grizant/n1pas/tree/master"
                        ],
                        "owner" : "grizant",
                        "repo" : "n1pas",
                        "res" : {
                            "concept" : "R package for N-of-1-pathways Alternatively Spliced",
                            "creationDate" : "2019-04-02T14:21:17Z",
                            "desc" : "R package for N-of-1-pathways Alternatively Spliced",
                            "has_compiledLanguages" : False,
                            "has_help" : True,
                            "has_interpretedLanguages" : True,
                            "has_issue_tracker" : True,
                            "has_license" : True,
                            "has_tutorial" : True,
                            "has_website" : True,
                            "issues" : {
                                "closed" : 0,
                                "lastClosedDate" : None,
                                "lastCreatedDate" : None,
                                "lastUpdatedDate" : None,
                                "open" : 0,
                                "total" : 0
                            },
                            "languages" : [
                                "R",
                                "Rebol"
                            ],
                            "lastPush" : "2019-04-03T00:40:18Z",
                            "lastUpdate" : "2019-04-03T00:40:19Z",
                            "numForks" : 1,
                            "numWatchers" : 0,
                            "owner" : "grizant",
                            "readmeFile" : "README.Rmd",
                            "repo" : "n1pas",
                            "source_hasAnonymousAccess" : True,
                            "source_hasVcsRepo" : True,
                            "source_isDownloadRegistered" : False,
                            "source_isFree" : True,
                            "source_isRepoAccessible" : True,
                            "source_isRepoBrowsable" : True,
                            "source_license" : "NOASSERTION",
                            "source_license_uri" : "https://github.com/grizant/n1pas/blob/master/LICENSE",
                            "source_uri" : "https://github.com/grizant/n1pas.git",
                            "tool_license_uri" : "https://github.com/grizant/n1pas/blob/master/LICENSE",
                            "tool_developers" : [
                                    {
                                        "location" : "San Francisco, CA",
                                        "name" : "Nigel Delaney",
                                        "username" : "evolvedmicrobe"
                                    },
                                    {
                                        "company" : "Microsoft",
                                        "location" : "Dallas, Texas",
                                        "name" : "Mark Smith",
                                        "username" : "markjulmar"
                                    },
                                    {
                                        "username" : "jjby"
                                    },
                                    {
                                        "company" : "KTH Royal Institute of Technology",
                                        "location" : "Stockholm, Sweden",
                                        "name" : "Anthony",
                                        "username" : "acesnik"
                                    },
                                    {
                                        "name" : "Charles Patrick Moore",
                                        "username" : "cpatmoore"
                                    }
                                ],
                            "vcs_type" : "git",
                            "vcs_uri" : "https://github.com/grizant/n1pas.git",
                            "website" : "https://github.com/grizant/n1pas",
                            "workspace" : "grizant"
                        },
                        "workspace" : "grizant"
                    }
                ]
            }
        ]

        generator = repositoryToolsGenerator(tools)
        assert len(generator.instSet.instances) == 1

        instance = generator.instSet.instances[0]
        assert instance.name == "n1pas"
        assert instance.version == []
        assert instance.type == software_types.lib
        assert instance.download == []
        assert instance.source == [ data_sources.github ]
        assert instance.webpage == [ HttpUrl("https://github.com/grizant/n1pas") ]
        assert instance.description == ["R package for N-of-1-pathways Alternatively Spliced."]
        assert instance.source_code == [ HttpUrl('https://github.com/grizant/n1pas.git') ]
        assert instance.languages == ["R", "Rebol"]
        assert instance.inst_instr == True
        assert [item.model_dump() for item in instance.repository] == [
            {
                'kind': repository_kind.github,
                'url': HttpUrl('https://github.com/grizant/n1pas'),
                'source_hasAnonymousAccess': True,
                'source_isDownloadRegistered': False,
                'source_isFree': True,
                'source_isRepoAccessible': True
            }
        ]
        assert [item.model_dump() for item in instance.license] == [{
            'name': 'NOASSERTION',
            'url': HttpUrl('https://github.com/grizant/n1pas/blob/master/LICENSE')
        }]
        assert [item.model_dump() for item in instance.authors] == [
            {
                'name': 'evolvedmicrobe', 
                'url': HttpUrl('https://github.com/evolvedmicrobe'), 
                'type': type_contributor.Person,
                'maintainer': False,
                'email': None,
                'orcid': None
            }, 
            {
                'name': 'markjulmar', 
                'url': HttpUrl('https://github.com/markjulmar'), 
                'type': type_contributor.Person,
                'maintainer': False,
                'email': None,
                'orcid': None
            }, 
            {
                'name': 'jjby', 
                'url': HttpUrl('https://github.com/jjby'), 
                'type': type_contributor.Person,
                'maintainer': False,
                'email': None,
                'orcid': None
            }, 
            {
                'name': 'acesnik', 
                'url': HttpUrl('https://github.com/acesnik'), 
                'type': type_contributor.Person,
                'maintainer': False,
                'email': None,
                'orcid': None
            }, 
            {
                'name': 'cpatmoore', 
                'url': HttpUrl('https://github.com/cpatmoore'), 
                'type': type_contributor.Person,
                'maintainer': False,
                'email': None,
                'orcid': None
            }
        ]
        assert [item.model_dump() for item in instance.license] == [
            {
                'name': 'NOASSERTION',
                'url': HttpUrl('https://github.com/grizant/n1pas/blob/master/LICENSE')
            }
        ]

    def test_transform_tool_with_empty_fields_filled_correctly(self):
        tools = [
            {
                "_id" : 'ObjectId("602a96dd651dd46a70b0836c")',
                "@id" : "https://openebench.bsc.es/monitor/tool/repository:n1pas/lib",
                "@data_source" : "repository",
                "entry_links" : [],
                "repos" : [
                    {
                        "instance" : None,
                        "kind" : "github",
                        "links" : [
                            "https://github.com/grizant/n1pas/tree/master"
                        ],
                        "owner" : "grizant",
                        "repo" : "n1pas",
                        "res" : {}
                        }
                ]
            }]

        generator = repositoryToolsGenerator(tools)
        assert len(generator.instSet.instances) == 1


    def test_transform_tool_with_missing_fields(self):
        '''
        This test checks that the generator raises an EXCEPTION when the input dictionary is missing the "repos" field.
        This metadata dictionary has no relevant information and will be skipped after the error is raised.
        '''
        tools = [
            {
                "_id" : 'ObjectId("602a96dd651dd46a70b0836c")',
                "@id" : "https://openebench.bsc.es/monitor/tool/repository:n1pas/lib",
                "@data_source" : "repository",
                "entry_links" : [],
                "repos" : []
            }]
        
        
        generator = repositoryToolsGenerator(tools)
        assert len(generator.instSet.instances) == 0

