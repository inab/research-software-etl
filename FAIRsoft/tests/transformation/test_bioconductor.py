from FAIRsoft.transformation.bioconductor import bioconductorToolsGenerator
from FAIRsoft.classes.main import software_types, operating_systems, data_sources
from FAIRsoft.classes.recognition import type_contributor
from FAIRsoft.classes.repository import repository_kind
from pydantic import HttpUrl

class TestBioconductorToolsGenerator:

    def test_transform_single_tool(self):
        tools = [{
                "_id" : 'ObjectId("6397235c7f087e4dfceecd75")',
                "@id" : "https://openebench.bsc.es/monitor/tool/bioconductor:a4:1.46.0/lib",
                "@data_source" : "bioconductor",
                "@source_url" : "https://bioconductor.org/packages/release/bioc/html/a4.html",
                "Build Report" : None,
                "Depends" : [
                    "a4Base",
                    "a4Preproc",
                    "a4Classif",
                    "a4Core",
                    "a4Reporting"
                ],
                "Depends On Me" : None,
                "Enhances" : None,
                "Imports" : None,
                "Imports Me" : None,
                "In Bioconductor since" : "BioC2.8(R-2.13)(12years)",
                "Installation instructions" : None,
                "License" : "GPL-3",
                "LinkingTo" : None,
                "Links To Me" : None,
                "Package Downloads Report" : "DownloadStats",
                "Package Short Url" : "https://bioconductor.org/packages/a4/",
                "Source Package" : "a4_1.46.0.tar.gz",
                "Source Repository" : "gitclonehttps://git.bioconductor.org/packages/a4",
                "Source Repository (Developer Access)" : "gitclonegit@git.bioconductor.org:packages/a4",
                "Suggests" : [
                    "MLP",
                    "nlcv",
                    "ALL",
                    "Cairo",
                    "Rgraphviz",
                    "GOstats"
                ],
                "Suggests Me" : None,
                "SystemRequirements" : None,
                "URL" : None,
                "Version" : "1.46.0",
                "Windows Binary" : "a4_1.46.0.zip",
                "authors" : [
                    " Willem Talloen [aut]",
                    " Tobias Verbeke [aut]",
                    " Laure Cougnaud [cre] "
                ],
                "biocViews" : "Microarray,Software",
                "citation" : 1,
                "description" : "Umbrella package is available for the entire Automated Affymetrix Array Analysis suite of package.",
                "documentation" : {
                    "a4vignette" : "https://bioconductor.org/vignettes/a4/inst/doc/a4vignette.pdf",
                    "Reference Manual" : "https://bioconductor.org/manuals/a4/man/a4.pdf",
                    "NEWS" : "https://bioconductor.org/news/a4/NEWS"
                },
                "links" : [
                    "https://bioconductor.org/packages/release/bioc/html/a4.html"
                ],
                "macOS Binary (arm64)" : "a4_1.46.0.tgz",
                "macOS Binary (x86_64)" : "a4_1.46.0.tgz",
                "mantainers" : [
                    " Laure Cougnaud <laure.cougnaud at openanalytics.eu> "
                ],
                "name" : "a4",
                "publication" : {
                    "url" : None,
                    "citation" : {
                        "author" : [
                            {
                                "family" : "Talloen",
                                "given" : "W."
                            },
                            {
                                "family" : "Verbeke",
                                "given" : "T."
                            }
                        ],
                        "date" : [
                            "2022"
                        ],
                        "title" : [
                            "a4: Automated Affymetrix Array Analysis Umbrella Package"
                        ],
                        "genre" : [
                            "R package version 1.46.0."
                        ],
                        "type" : None
                    }
                },
                "@date" : "2023-02-27T09:38:43.193367",
                "Bioc Package Browser" : "https://code.bioconductor.org/browse/a4/"
            }]
        
        generator = bioconductorToolsGenerator(tools)
        assert len(generator.instSet.instances) == 1

        tool = generator.instSet.instances[0]
        assert tool.name == 'a4'
        assert tool.version == ['1.46.0']
        assert tool.type == software_types.lib
        assert tool.source == [data_sources.bioconductor]
        assert tool.description == ['Umbrella package is available for the entire Automated Affymetrix Array Analysis suite of package.']
        assert tool.webpage == [HttpUrl('https://bioconductor.org/packages/release/bioc/html/a4.html')]
        assert tool.publication == []
        assert set(tool.download) == set([
            HttpUrl('https://bioconductor.org/packages/a4/a4_1.46.0.tar.gz'),
            HttpUrl('https://bioconductor.org/packages/a4/a4_1.46.0.tgz'),
            HttpUrl('https://bioconductor.org/packages/a4/a4_1.46.0.zip')
        ])
        assert tool.source_code == [HttpUrl('https://bioconductor.org/packages/a4/a4_1.46.0.tar.gz')]
        assert set(tool.operating_system) == set([operating_systems.Linux, operating_systems.macOS, operating_systems.Windows])
        assert [item.model_dump() for item in tool.license] == [{
            'name': 'GPL-3.0-only',
            'url': HttpUrl('https://spdx.org/licenses/GPL-3.0-only.html')
        }]
        assert tool.label == ['a4']
        assert tool.dependencies == ['a4Base', 'a4Preproc', 'a4Classif', 'a4Core', 'a4Reporting']
        assert [item.model_dump() for item in tool.authors] == [
            {
                'type': type_contributor.Person,
                'name': 'Laure Cougnaud',
                'email': 'laure.cougnaud@openanalytics.eu',
                'maintainer': True,
                'url': None,
                'orcid': None
            },
            {
                'type': type_contributor.Person,
                'name': 'Willem Talloen',
                'email': None,
                'maintainer': False,
                'url': None,
                'orcid': None
            },
            {
                'type': type_contributor.Person,
                'name': 'Tobias Verbeke',
                'email': None,
                'maintainer': False,
                'url': None,
                'orcid': None
            }
        ]
        assert [item.model_dump() for item in  tool.repository] == [
            {
                'kind': repository_kind.bioconductor,
                'url': HttpUrl('https://git.bioconductor.org/packages/a4'),
                'source_hasAnonymousAccess': None,
                'source_isDownloadRegistered': None,
                'source_isFree': None,
                'source_isRepoAccessible': None
            }
        ]
        assert [item.model_dump() for item in tool.documentation] == [
            {
                'type': 'a4vignette',
                'url': HttpUrl('https://bioconductor.org/vignettes/a4/inst/doc/a4vignette.pdf'),
                'content': None
            },
            {
                'type': 'Reference Manual',
                'url': HttpUrl('https://bioconductor.org/manuals/a4/man/a4.pdf'),
                'content': None
            },
            {
                'type': 'NEWS',
                'url': HttpUrl('https://bioconductor.org/news/a4/NEWS'),
                'content': None
            }
        ]

    def test_transform_tool_with_empty_fields_filled_correctly(self):
        tools = [            
            {
                "_id" : 'ObjectId("6397235c7f087e4dfceecd75")',
                "@id" : "https://openebench.bsc.es/monitor/tool/bioconductor:a4:1.46.0/lib",
                "@data_source" : "bioconductor",
                "@source_url" : "https://bioconductor.org/packages/release/bioc/html/a4.html",
                "Build Report" : None,
                "Depends" : [],
                "Depends On Me" : None,
                "Enhances" : None,
                "Imports" : None,
                "Imports Me" : None,
                "In Bioconductor since" : None,
                "Installation instructions" : None,
                "License" : "GPL-3",
                "LinkingTo" : None,
                "Links To Me" : None,
                "Package Downloads Report" : "DownloadStats",
                "Package Short Url" : None,
                "Source Package" : None,
                "Source Repository" : "gitclonehttps://git.bioconductor.org/packages/a4",
                "Source Repository (Developer Access)" : "gitclonegit@git.bioconductor.org:packages/a4",
                "Suggests" : [],
                "Suggests Me" : None,
                "SystemRequirements" : None,
                "URL" : None,
                "Version" : "1.46.0",
                "Windows Binary" : None,
                "authors" : [],
                "biocViews" : "Microarray,Software",
                "citation" : 1,
                "description" : None,
                "documentation" : {},
                "links" : [],
                "macOS Binary (arm64)" : None,
                "macOS Binary (x86_64)" : None,
                "mantainers" : [],
                "name" : "a4",
                "publication" : {},
                "@date" : "2023-02-27T09:38:43.193367",
                "Bioc Package Browser" : "https://code.bioconductor.org/browse/a4/"
            }]
        
        generator = bioconductorToolsGenerator(tools)
        assert len(generator.instSet.instances) == 1
        
