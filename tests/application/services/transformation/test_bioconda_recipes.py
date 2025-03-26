from src.application.services.transformation.bioconda_recipes import biocondaRecipesStandardizer
from src.domain.models.software_instance.main import software_types, operating_systems, data_sources
from src.domain.models.software_instance.recognition import type_contributor
from pydantic import HttpUrl
from dotenv import load_dotenv

class TestBiocondaRecipesStandardizer:

    # Transforms a single tool into an instance correctly.
    def test_transform_single_tool(self, mocker):
        load_dotenv('./.env')
        tool={
                '_id': 'bioconda_recipes/ucsc-chainnet/cmd/455',
                '@last_updated_at': "2024-02-28T15:34:11.722Z",
                '@updated_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/biconda-importer/-/commit/96e7639eab516a89f6a7ddece0252c16aef1491f',
                '@updated_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/biconda-importer/-/pipelines/120716',
                '@created_at': "2024-02-28T15:34:11.722Z",
                '@created_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/biconda-importer/-/commit/96e7639eab516a89f6a7ddece0252c16aef1491f',
                '@created_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/biconda-importer/-/pipelines/120716',
                'data': {
                    "_id" : 'ObjectId("63987bbe7f087e4dfcef6ed1")',
                    "@id" : "https://openebench.bsc.es/monitor/tool/bioconda_recipes:bioconductor-mafdb.gnomadex.r2.1.hs37d5:None/['lib']",
                    "@data_source" : "bioconda_recipes",
                    "about" : {
                        "home" : "https://bioconductor.org/packages/3.16/data/annotation/html/MafDb.gnomADex.r2.1.hs37d5.html",
                        "license" : "Artistic-2.0",
                        "summary" : "Minor allele frequency data from gnomAD exomes release 2.1 for hs37d5",
                        "description" : "Store minor allele frequency data from the Genome Aggregation Database (gnomAD exomes release 2.1) for the human genome version hs37d5.",
                        "authors" : "Xiaoqiu Huang and Anup Madan",
                        "maintainers": ["evamart", "Anup Madan" ]
                    },
                    "build" : {
                        "number" : "7",
                        "rpaths" : [
                            "lib/R/lib/",
                            "lib/"
                        ],
                        "noarch" : "generic"
                    },
                    "name" : "bioconductor-mafdb.gnomadex.r2.1.hs37d5",
                    "package" : {
                        "name" : "bioconductor-mafdb.gnomadex.r2.1.hs37d5",
                        "version" : "3.10.0"
                    },
                    "requirements" : {
                        "host" : [
                            "bioconductor-bsgenome >=1.66.0,<1.67.0",
                            "bioconductor-genomeinfodb >=1.34.0,<1.35.0",
                            "bioconductor-genomicranges >=1.50.0,<1.51.0",
                            "bioconductor-genomicscores >=2.10.0,<2.11.0",
                            "bioconductor-iranges >=2.32.0,<2.33.0",
                            "bioconductor-s4vectors >=0.36.0,<0.37.0",
                            "r-base"
                        ],
                        "run" : [
                            "bioconductor-bsgenome >=1.66.0,<1.67.0",
                            "bioconductor-genomeinfodb >=1.34.0,<1.35.0",
                            "bioconductor-genomicranges >=1.50.0,<1.51.0",
                            "bioconductor-genomicscores >=2.10.0,<2.11.0",
                            "bioconductor-iranges >=2.32.0,<2.33.0",
                            "bioconductor-s4vectors >=0.36.0,<0.37.0",
                            "r-base",
                            "curl",
                            "bioconductor-data-packages>=20221103"
                        ]
                    },
                    "source" : {
                        "url" : [
                            "https://bioconductor.org/packages/3.16/data/annotation/src/contrib/MafDb.gnomADex.r2.1.hs37d5_3.10.0.tar.gz",
                            "https://bioarchive.galaxyproject.org/MafDb.gnomADex.r2.1.hs37d5_3.10.0.tar.gz",
                            "https://depot.galaxyproject.org/software/bioconductor-mafdb.gnomadex.r2.1.hs37d5/bioconductor-mafdb.gnomadex.r2.1.hs37d5_3.10.0_src_all.tar.gz"
                        ],
                        "md5" : "6ca4d742571687a13906d99cea2dbf1f"
                    },
                    "test" : {
                        "commands" : [
                            "$R -e \"library('MafDb.gnomADex.r2.1.hs37d5')\""
                        ]
                    },
                    "@type" : "lib"
                }
            }
        
        
        generator = biocondaRecipesStandardizer()
        standardized_tools = generator.process_transformation(tool)
        assert len(standardized_tools) == 1

        instance = standardized_tools[0]
        assert instance.name == 'bioconductor-mafdb.gnomadex.r2.1.hs37d5'
        assert instance.type == software_types.lib
        assert instance.version == ['3.10.0']
        assert instance.source == [data_sources.bioconda_recipes]
        assert instance.label == ['bioconductor-mafdb.gnomadex.r2.1.hs37d5']
        assert instance.description == ['Store minor allele frequency data from the Genome Aggregation Database (gnomAD exomes release 2.1) for the human genome version hs37d5.']
        assert instance.webpage == [HttpUrl('https://bioconductor.org/packages/3.16/data/annotation/html/MafDb.gnomADex.r2.1.hs37d5.html')]
        assert instance.source_code == [
                        HttpUrl("https://bioconductor.org/packages/3.16/data/annotation/src/contrib/MafDb.gnomADex.r2.1.hs37d5_3.10.0.tar.gz"),
                        HttpUrl("https://depot.galaxyproject.org/software/bioconductor-mafdb.gnomadex.r2.1.hs37d5/bioconductor-mafdb.gnomadex.r2.1.hs37d5_3.10.0_src_all.tar.gz"),
                        HttpUrl("https://bioarchive.galaxyproject.org/MafDb.gnomADex.r2.1.hs37d5_3.10.0.tar.gz") 
                    ]
        assert [item.model_dump() for item in instance.documentation ] ==[
            {
                'url': HttpUrl('https://bioconda.github.io/recipes/bioconductor-mafdb.gnomadex.r2.1.hs37d5/README.html'),
                'type': 'installation_instructions',
                'content': None
            },
            {
                'url': HttpUrl('https://bioconda.github.io/recipes/bioconductor-mafdb.gnomadex.r2.1.hs37d5/README.html'),
                'type': 'general',
                'content': None
            }
        ]
        assert instance.repository == []
        assert instance.operating_system == [ operating_systems.Linux, operating_systems.macOS, operating_systems.Windows]
        assert [item.model_dump() for item in instance.license ] == [
            {
                'name': 'Artistic-2.0',
                'url': HttpUrl('https://spdx.org/licenses/Artistic-2.0.html')
            }
        ]
        
        assert instance.publication == []
        assert instance.dependencies == [
                        "bioconductor-bsgenome >=1.66.0,<1.67.0",
                        "bioconductor-genomeinfodb >=1.34.0,<1.35.0",
                        "bioconductor-genomicranges >=1.50.0,<1.51.0",
                        "bioconductor-genomicscores >=2.10.0,<2.11.0",
                        "bioconductor-iranges >=2.32.0,<2.33.0",
                        "bioconductor-s4vectors >=0.36.0,<0.37.0",
                        "r-base",
                        "curl",
                        "bioconductor-data-packages>=20221103"
                    ]
        
        assert [item.model_dump() for item in instance.authors] == [
                        {
                            'name': None,
                            'type': type_contributor.Person,
                            'url': HttpUrl('https://github.com/evamart'),
                            'email': None,
                            'orcid': None,
                            'maintainer': True
                        },
                        {
                            'name': 'Anup Madan',
                            'type': type_contributor.Person,
                            'url': None,
                            'email': None,
                            'orcid': None,
                            'maintainer': True
                        },  
                        {
                            'name': 'Xiaoqiu Huang',
                            'type': type_contributor.Person,
                            'url': None,
                            'email': None,
                            'orcid': None,
                            'maintainer': False
                        },
                        ]
                        
                        
# TODO: add bioconda recipe test for a tool with repository


        