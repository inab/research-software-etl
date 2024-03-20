from FAIRsoft.transformation.biotools_opeb import biotoolsOPEBToolsGenerator
from FAIRsoft.classes.main import software_types, operating_systems, data_sources
from FAIRsoft.classes.recognition import type_contributor
from FAIRsoft.classes.repository import repository_kind

from pydantic import HttpUrl, EmailStr

class TestTransform:

    # Transforms a tool with all fields filled correctly
    def test_transform_tool_with_all_fields_filled_correctly(self):
        tools = [
            {
                "@id" : "https://openebench.bsc.es/monitor/tool/biotools:ps2-v3:3.0/web/ps2v3.life.nctu.edu.tw",
                "@data_source" : "biotools",
                "@label" : "ps2-v3",
                "@license" : "https://creativecommons.org/licenses/by/4.0/",
                "@nmsp" : "biotools",
                "@source_url" : "https://openebench.bsc.es/monitor/tool/biotools:ps2-v3:3.0/web/ps2v3.life.nctu.edu.tw",
                "@timestamp" : "2023-02-27T02:45:23.295125Z",
                "@type" : "web",
                "@version" : "3.0",
                "alt_ids" : [],
                "confidence" : "ultimate",
                "contacts" : [],
                "credits" : [
                    {
                        "email" : "chieh.bi91g@nctu.edu.tw",
                        "type" : "Person",
                        "url" : "http://mbc.nctu.edu.tw/"
                    }
                ],
                "description" : "Automated homology modeling server. The method uses an effective consensus strategy by combining PSI-BLAST, IMPALA, and T-Coffee in both template selection and target-template alignment. The final three dimensional structure is built using the modeling package MODELLER.",
                "documentation" : {
                    "doc_links" : [],
                    "general" : "http://ps2v3.life.nctu.edu.tw/help.php"
                },
                "languages" : [],
                "name" : "(PS)2 - v3",
                "os" : [
                    "Linux",
                    "Windows",
                    "Mac"
                ],
                "publications" : [
                    {
                        "pmid" : "25943546"
                    }
                ],
                "license" : ['MIT'],
                "repositories" : ["https://github.com/bene51/3Dscripts"],
                "semantics" : {
                    "inputs" : [{
                            "datatype" : "http://edamontology.org/data_2610",
                            "formats" : []
                        },
                        {
                            "datatype" : "http://edamontology.org/data_3498",
                            "formats" : [
                                "http://edamontology.org/format_3016"
                            ]
                        }    
                    ],
                    "operations" : [
                        "http://edamontology.org/operation_0474",
                        "http://edamontology.org/operation_2479"
                    ],
                    "outputs" : [
                        {
                            "datatype" : "http://edamontology.org/data_2610",
                            "formats" : []
                        },
                        {
                            "formats" : [
                                "http://edamontology.org/format_2330",
                                "http://edamontology.org/format_2331"
                            ]
                        },
                        {
                            "datatype" : "http://edamontology.org/data_0897",
                            "formats" : [
                                "http://edamontology.org/format_2331"
                            ]
                        }
                    ],
                    "topics" : [
                        "http://edamontology.org/topic_0082",
                        "http://edamontology.org/topic_2275",
                        "http://edamontology.org/topic_2814",
                        "http://edamontology.org/topic_0078"
                    ]
                },
                "tags" : ["Proteomics"],
                "validated" : 1,
                "web" : {
                    "homepage" : "http://ps2v3.life.nctu.edu.tw/"
                }
            }
        ]

        biotools_generator = biotoolsOPEBToolsGenerator(tools)

        assert len(biotools_generator.instSet.instances) == 1
        instance = biotools_generator.instSet.instances[0]
        assert instance.name == ("ps2-v3")
        assert instance.type == software_types.web
        assert instance.version == ['3.0']
        assert instance.source == [data_sources.biotools]
        assert instance.label == ['(PS)2 - v3']
        assert instance.description == ['Automated homology modeling server. The method uses an effective consensus strategy by combining PSI-BLAST, IMPALA, and T-Coffee in both template selection and target-template alignment. The final three dimensional structure is built using the modeling package MODELLER.']
        assert [item.model_dump() for item in instance.publication] == [{'cit_count':None, 'citations':[], 'doi':None, 'pmcid':None, 'pmid':'25943546', 'title':None, 'year':None, 'ref_count':None, 'refs':[], 'pmid': '25943546'}]
        assert instance.test == False
        assert [item.model_dump() for item in  instance.license] == [{
                                                                        'name': 'MIT',
                                                                        'url': HttpUrl('https://spdx.org/licenses/MIT.html'),
                                                                    }]
        assert [item.model_dump() for item in  instance.documentation ] == [{'type':'general', 'url': HttpUrl('http://ps2v3.life.nctu.edu.tw/help.php'), 'content': None}]
        assert instance.operating_system == [operating_systems.Linux, operating_systems.Windows, operating_systems.macOS]
        assert [item.model_dump() for item in  instance.repository] == [{ 
                                                                            'url': HttpUrl('https://github.com/bene51/3Dscripts'),
                                                                            'kind': repository_kind.github,
                                                                            'source_hasAnonymousAccess': None,
                                                                            'source_isDownloadRegistered': None,
                                                                            'source_isFree': None,
                                                                            'source_isRepoAccessible': None                                                                        
                                                                        }]
        assert instance.webpage == [HttpUrl('http://ps2v3.life.nctu.edu.tw/')]
        assert [item.model_dump() for item in instance.input] == [{
                                            'vocabulary': '', 
                                            'term': '', 
                                            'uri': None, 
                                            'datatype': {
                                                'vocabulary': 'EDAM', 
                                                'term': 'Ensembl ID', 
                                                'uri': HttpUrl('http://edamontology.org/data_2610')
                                                }
                                        },
                                        {
                                            'vocabulary': 'EDAM',
                                            'term': 'VCF', 
                                            'uri': HttpUrl('http://edamontology.org/format_3016'), 
                                            'datatype': {
                                                'vocabulary': 'EDAM', 
                                                'term': 'Sequence variations', 
                                                'uri': HttpUrl('http://edamontology.org/data_3498')}
                                        }]
        assert [item.model_dump() for item in instance.output] ==  [{
                                            'vocabulary': '',
                                            'term': '', 
                                            'uri': None, 
                                            'datatype': {
                                                'vocabulary': 'EDAM', 
                                                'term': 'Ensembl ID', 
                                                'uri': HttpUrl('http://edamontology.org/data_2610')
                                            }
                                        }, 
                                        {
                                            'vocabulary': 'EDAM', 
                                            'term': 'Textual format', 
                                            'uri': HttpUrl('http://edamontology.org/format_2330'), 
                                            'datatype': {
                                                'vocabulary': '', 
                                                'term': '', 
                                                'uri': None
                                            }
                                        }, 
                                        {
                                            'vocabulary': 'EDAM', 
                                            'term': 'HTML', 
                                            'uri': HttpUrl('http://edamontology.org/format_2331'), 
                                            'datatype': {
                                                'vocabulary': '', 
                                                'term': '', 
                                                'uri': None
                                            }
                                        }, 
                                        {
                                            'vocabulary': 'EDAM', 
                                            'term': 'HTML', 
                                            'uri': HttpUrl('http://edamontology.org/format_2331'), 
                                            'datatype': {
                                                'vocabulary': 'EDAM', 
                                                'term': 'Protein property', 
                                                'uri': HttpUrl('http://edamontology.org/data_0897')
                                            }
                                        }]
        assert [item.model_dump() for item in instance.topics] == [{
                                            'vocabulary':'EDAM',
                                            'uri':HttpUrl('http://edamontology.org/topic_0082'),
                                            'term':'Structure prediction',
                                         },
                                        {
                                            'vocabulary':'EDAM',
                                            'uri':HttpUrl('http://edamontology.org/topic_2275'),
                                            'term':'Molecular modelling',
                                        },
                                        {
                                            'vocabulary':'EDAM',
                                            'uri':HttpUrl('http://edamontology.org/topic_2814'),
                                            'term':'Protein structure analysis',
                                        },
                                        {
                                            'vocabulary':'EDAM',
                                            'uri':HttpUrl('http://edamontology.org/topic_0078'),
                                            'term':'Proteins',
                                        }
                                    ]
        assert [item.model_dump() for item in instance.operations] == [{
                                                'vocabulary':'EDAM',
                                                'uri': HttpUrl('http://edamontology.org/operation_0474'),
                                                'term':'Protein structure prediction',
                                            },
                                            {
                                                'vocabulary':'EDAM',
                                                'uri': HttpUrl('http://edamontology.org/operation_2479'),
                                                'term':'Protein sequence analysis',
                                            }]
        assert [item.model_dump() for item in instance.authors] == [{
                        "email" : "chieh.bi91g@nctu.edu.tw",
                        "type" : type_contributor("Person"),
                        "url" : HttpUrl("http://mbc.nctu.edu.tw/"),
                        "name": None,
                        "maintainer": False,
                        "orcid": None
                    }]
        assert instance.tags == ['Proteomics']

    # Transforms a tool with empty fields
    def test_transform_tool_with_empty_fields_filled_correctly(self):
        tools = [{
                "@id" : "https://openebench.bsc.es/monitor/tool/biotools:ps2-v3:3.0/web/ps2v3.life.nctu.edu.tw",
                "@data_source" : "biotools",
                "@label" : "ps2-v3",
                "@license" : "https://creativecommons.org/licenses/by/4.0/",
                "@nmsp" : "biotools",
                "@source_url" : "https://openebench.bsc.es/monitor/tool/biotools:ps2-v3:3.0/web/ps2v3.life.nctu.edu.tw",
                "@timestamp" : "2023-02-27T02:45:23.295125Z",
                "@type" : "web",
                "@version" : "3.0",
                "alt_ids" : [],
                "confidence" : "ultimate",
                "contacts" : [],
                "credits" : [],
                "description" : "",
                "documentation" : {
                    "doc_links" : [],
                    "general" : ""
                },
                "languages" : [],
                "name" : "",
                "os" : [],
                "publications" : [],
                "license" : [],
                "repositories" : [],
                "semantics" : {
                    "inputs" : [],
                    "operations" : [],
                    "outputs" : [],
                    "topics" : []
                },
                "tags" : [],
                "validated" : 1,
                "web" : {
                    "homepage" : ""
                }
            }
        ]

        biotools_generator = biotoolsOPEBToolsGenerator(tools)

        assert len(biotools_generator.instSet.instances) == 1
        instance = biotools_generator.instSet.instances[0]
        assert instance.name == "ps2-v3"
        assert instance.type == software_types.web
        assert instance.version == ['3.0']
        assert instance.source == ['biotools']
        assert instance.label == ['ps2-v3']
        assert instance.description == []
        assert [item.model_dump() for item in instance.publication] == []
        assert instance.test == False
        assert [item.model_dump() for item in  instance.license] == []
        assert [item.model_dump() for item in  instance.documentation ] == []
        assert instance.operating_system == []
        assert instance.repository == []
        assert instance.webpage == []
        assert [item.model_dump() for item in instance.input] == []
        assert [item.model_dump() for item in instance.output] == []
        assert [item.model_dump() for item in instance.topics] == []
        assert [item.model_dump() for item in instance.operations] == []
        assert [item.model_dump() for item in instance.authors] == []
        assert instance.tags == []
        
    
    # with missing fields
    def test_transform_tool_with_missing_fields(self):
        tools = [{
            "@id" : "https://openebench.bsc.es/monitor/tool/biotools:ps2-v3:3.0/web/ps2v3.life.nctu.edu.tw",
                "@data_source" : "biotools",
                "@label" : "ps2-v3",
                "@license" : "https://creativecommons.org/licenses/by/4.0/",
                "@nmsp" : "biotools",
                "@source_url" : "https://openebench.bsc.es/monitor/tool/biotools:ps2-v3:3.0/web/ps2v3.life.nctu.edu.tw",
                "@timestamp" : "2023-02-27T02:45:23.295125Z",
                "@type" : "web",
                "@version" : "3.0",
                "alt_ids" : [],
                "confidence" : "ultimate",
                "contacts" : [],
                'name': 'ps2-v3'
            }]
        
        biotools_generator = biotoolsOPEBToolsGenerator(tools)

        assert len(biotools_generator.instSet.instances) == 1
        instance = biotools_generator.instSet.instances[0]
        assert instance.name == ("ps2-v3")
        assert instance.type == software_types.web
        assert instance.version == ['3.0']
        assert instance.source == ['biotools']
        assert instance.label == ['ps2-v3']
        assert instance.description == []
        assert [item.model_dump() for item in instance.publication] == []
        assert instance.test == False
        assert [item.model_dump() for item in  instance.license] == []
        assert [item.model_dump() for item in  instance.documentation ] == []
        assert instance.operating_system == []
        assert instance.repository == []
        assert instance.webpage == []
        assert [item.model_dump() for item in instance.input] == []
        assert [item.model_dump() for item in instance.output] == []
        assert [item.model_dump() for item in instance.topics] == []
        assert [item.model_dump() for item in instance.operations] == []
        assert [item.model_dump() for item in instance.authors] == []
        assert instance.tags == []
        