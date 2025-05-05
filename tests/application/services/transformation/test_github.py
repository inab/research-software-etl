from src.application.services.transformation.github import githubStandardizer
from pydantic import HttpUrl


class TestGitHubStandardizer:

    def test_transform_single_tool(self):
        tool = {
            '_id': 'github/HybPiper',
            '@last_updated_at': "2025-01-20T14:44:38.307Z",
            '@updated_by': 'https://gitlab.bsc.es/None/None/-/commit/None',
            '@updated_logs': None,
            '@created_at': "2025-01-20T14:44:38.307Z",
            '@created_by': 'https://gitlab.bsc.es/None/None/-/commit/None',
            '@created_logs': None,
            '@data_source': 'github',
            '@source_url': 'https://github.com/mossmatters/HybPiper',
            'data': {
                'name': 'HybPiper',
                'label': ['HybPiper'],
                'description': ['Recovering genes from targeted sequence capture data'],
                'links': [],
                'webpage': [''],
                'isDisabled': False,
                'isEmpty': False,
                'isLocked': False,
                'isPrivate': False,
                'isTemplate': False,
                'version': [
                    'v2.3.2',       'v2.3.1',
                    'v2.3.0',       'v2.2.0',
                    'v2.1.8',       'v2.1.7',
                    'v2.1.6',       'v2.1.5',
                    'v2.1.4',       'v2.1.3',
                    'v2.1.1',       'v2.0.2',
                    'v1.3.1_final', 'v1.3.1',
                    'v1.3',         'v1.2.0',
                    'v1.1',         'v1.0.0',
                    'v0.4.3',       'v0.4.0',
                    'v0.3.0',       '0.2.0',
                    '0.1.0',        '0.0.2',
                    '0.0.1'
                ],
                'license': [
                    {
                        'name': 'GNU General Public License v3.0',
                        'url': 'http://choosealicense.com/licenses/gpl-3.0/'
                    }
                ],
                'repository': [ 'https://github.com/mossmatters/HybPiper' ],
                'documentation': [
                    {
                        'type': 'license',
                        'url': 'https://github.com/mossmatters/HybPiper/blob/main/LICENSE.txt'
                    },
                    {
                        'type': 'readme',
                        'url': 'https://github.com/mossmatters/HybPiper/blob/main/README.md'
                    },
                    {
                        'type': 'root',
                        'url': 'https://github.com/mossmatters/HybPiper/blob/main/change_log.md'
                    },
                    {
                        'type': 'root',
                        'url': 'https://github.com/mossmatters/HybPiper/blob/main/citation_list.txt'
                    }
                ],
                'authors': [
                    {
                        'name': 'KatharinaHoff',
                        'type': 'person',
                        'email': 'katharina.hoff@gmail.com',
                        'maintainer': False
                    },
                    {
                        'name': 'Lars Gabriel',
                        'type': 'person',
                        'email': 'gabriell@login-b.maas',
                        'maintainer': False
                    },
                    {
                        'name': 'Katharina Hoff',
                        'type': 'person',
                        'email': '39333668+KatharinaHoff@users.noreply.github.com',
                        'maintainer': False
                    }
                ],
                'download': [],
                'os': [],
                'publication': [],
                'topics' : []
            } 
        }

        generator = githubStandardizer()
        standardized_tools = generator.process_transformation(tool)
        assert len(standardized_tools) == 1
        instance = standardized_tools[0]

        assert instance.name == "HybPiper"
        assert len(instance.authors) == 3
        assert len(instance.license) == 1