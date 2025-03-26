from src.application.services.transformation.opeb_metrics import OPEBMetricsStandardizer
from src.domain.models.software_instance.main import software_types, data_sources
from pydantic import HttpUrl

class TestOpebMetricsStandardizer:

    # Transforms a single tool into an instance correctly.
    def test_transform_single_tool(self, mocker):
        tool = {
                '_id': 'opeb_metrics/alexa-seq//',
                '@last_updated_at': "2024-02-29T16:23:31.837Z",
                '@updated_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-metrics-importer/-/commit/06a5edb82031101800a65fd49d4ba688db8de449',
                '@updated_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-metrics-importer/-/pipelines/120989',
                '@created_at': "2024-02-29T16:23:31.837Z",
                '@created_by': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-metrics-importer/-/commit/06a5edb82031101800a65fd49d4ba688db8de449',
                '@created_logs': 'https://gitlab.bsc.es/inb/elixir/software-observatory/opeb-metrics-importer/-/pipelines/120989',
                'data': {
                    'project': {
                        'build': {},
                        'deployment': {},
                        'publications': [],
                        'summary': { 'description': True },
                        'website': {
                            'access_time': 433,
                            'bioschemas': False,
                            'last_check': '2024-02-29T02:32:00.292319Z',
                            'operational': 200,
                            'copyright': False,
                            'license': False,
                            'ssl': None,
                            'https': False,
                            'last_month_access': {
                                'average_access_time': 529,
                                'downtime_days': 0,
                                'uptime_days': 30
                            },
                            'half_year_stat': [ { 'days': 183, 'serie': [ 183 ], 'status': 200 } ],
                            'ssl_err': None
                        }
                    },
                    '@timestamp': '2024-02-29T02:32:00.367119Z',
                    '@id': 'https://openebench.bsc.es/monitor/metrics/biotools:alexa-seq:2.0-RC/cmd/trimal.cgenomics.org',
                    '@nmsp': None,
                    '@type': 'metrics',
                    '@license': 'https://creativecommons.org/licenses/by/4.0/',
                    'name': 'alexa-seq'
                },
                '@data_source': 'opeb_metrics'
            }

        generator = OPEBMetricsStandardizer()
        standardized_tools = generator.process_transformation(tool)

        assert len(standardized_tools) == 1

        instance = standardized_tools[0]