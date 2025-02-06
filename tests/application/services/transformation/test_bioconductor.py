from src.application.services.transformation.bioconductor import bioconductorStandardizer
from src.domain.models.software_instance.main import software_types, operating_systems, data_sources
from src.domain.models.software_instance.recognition import type_contributor
from src.domain.models.software_instance.repository import repository_kind
from pydantic import HttpUrl

class TestBioconductorStandardizer:

    def test_transform_single_tool(self):
        tool = {
            '_id': 'bioconductor/EnrichedHeatmap/lib/1.33.0',
            '@last_updated_at': "2024-03-18T17:22:04.586Z",
            '@updated_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/bioconductor-imoprter-v2/-/commit/180347cb5bae6b553663a670a560e13c40f1e64f',
            '@updated_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/bioconductor-imoprter-v2/-/pipelines/123886',
            'data': {
                'Type': 'Package',
                'Package': 'EnrichedHeatmap',
                'Title': 'Making Enriched Heatmaps',
                'Version': '1.33.0',
                'Date': '2023-03-19',
                'Authors@R (parsed)': [
                    {
                    'name': 'Zuguang Gu',
                    'roles': [ 'aut', 'cre' ],
                    'email': 'z.gu@dkfz.de',
                    'orcid': 'https://orcid.org/0000-0002-7395-8709'
                    }
                ],
                'Description': 'Enriched heatmap is a special type of heatmap which visualizes the enrichment of genomic signals on specific target regions.  Here we implement enriched heatmap by ComplexHeatmap package.  Since this type of heatmap is just a normal heatmap but with some special settings, with the functionality of ComplexHeatmap, it would be much easier to customize the heatmap as well as concatenating to a list of heatmaps to show correspondance between different data sources.',
                'License': [ 'MIT'],
                'URL': 'https://github.com/jokergoo/EnrichedHeatmap',
                'Depends': [
                    'ComplexHeatmap (>= 2.11.0)',
                    'GenomicRanges',
                    'grid',
                    'methods',
                    'R (>= 3.6.0)'
                ],
                'Imports': [
                    'circlize (>= 0.4.5)',
                    'GetoptLong',
                    'IRanges',
                    'locfit',
                    'matrixStats',
                    'Rcpp',
                    'stats',
                    'utils'
                ],
                'Suggests': [
                    'genefilter',
                    'knitr',
                    'markdown',
                    'RColorBrewer',
                    'rmarkdown',
                    'testthat (>= 0.3)'
                ],
                'LinkingTo': [ 'Rcpp' ],
                'VignetteBuilder': ' knitr',
                'biocViews': [
                    'Software',
                    'Visualization',
                    'Sequencing',
                    'GenomeAnnotation',
                    'Coverage'
                    ]
                },
            '@data_source': 'bioconductor',
            '@source_url': 'https://git.bioconductor.org/packages/EnrichedHeatmap',
            '@created_at': "2024-03-05T15:47:50.111Z",
            '@created_by': 'https://gitlab.bsc.es/None/None/-/commit/None',
            '@created_logs': None
        }
        
        generator = bioconductorStandardizer()
        standardized_tools = generator.process_transformation(tool)

        assert len(standardized_tools) == 1
        tool = standardized_tools[0]

        assert tool.name == 'enrichedheatmap'
        assert tool.version == ['1.33.0']
        assert tool.type == software_types.lib
        assert tool.source == [data_sources.bioconductor]
        assert tool.description == ['Enriched heatmap is a special type of heatmap which visualizes the enrichment of genomic signals on specific target regions.  Here we implement enriched heatmap by ComplexHeatmap package.  Since this type of heatmap is just a normal heatmap but with some special settings, with the functionality of ComplexHeatmap, it would be much easier to customize the heatmap as well as concatenating to a list of heatmaps to show correspondance between different data sources.']
        assert tool.webpage == [HttpUrl('https://github.com/jokergoo/EnrichedHeatmap')]
        assert tool.publication == []
        assert set(tool.download) == set()
        assert tool.source_code == []
        assert set(tool.operating_system) == set([operating_systems.Linux, operating_systems.macOS, operating_systems.Windows])
        assert [item.model_dump() for item in tool.license] == [{
            'name': 'MIT',
            'url': HttpUrl('https://spdx.org/licenses/MIT.html')
        }]
        assert tool.label == ['EnrichedHeatmap']
        assert set(tool.dependencies) == set(['circlize (>= 0.4.5)',
                    'GetoptLong',
                    'IRanges',
                    'locfit',
                    'matrixStats',
                    'Rcpp',
                    'stats',
                    'utils',
                    'ComplexHeatmap (>= 2.11.0)',
                    'GenomicRanges',
                    'grid',
                    'methods',
                    'R (>= 3.6.0)'])
        assert [item.model_dump() for item in tool.authors] == [
            {
                'type': type_contributor.Person,
                'name': 'Zuguang Gu',
                'email': 'z.gu@dkfz.de',
                'maintainer': False,
                'url': None,
                'orcid': 'https://orcid.org/0000-0002-7395-8709'
            }
        ]
        assert [item.model_dump() for item in  tool.repository] == [
            {
                'kind': repository_kind.bioconductor,
                'url': HttpUrl('https://git.bioconductor.org/packages/EnrichedHeatmap'),
                'source_hasAnonymousAccess': None,
                'source_isDownloadRegistered': None,
                'source_isFree': None,
                'source_isRepoAccessible': None
            }
        ]