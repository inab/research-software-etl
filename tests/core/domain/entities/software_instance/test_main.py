import pytest
from src.core.domain.entities.software_instance.main import instance, operating_systems
from src.core.domain.entities.software_instance.data_format import data_format, data_type
from src.core.domain.entities.software_instance.repository import repository_item
from src.core.domain.entities.software_instance.documentation import documentation_item
from src.core.domain.entities.software_instance.license import license_item
from src.core.domain.entities.software_instance.recognition import contributor
from src.core.domain.entities.software_instance.publication import publication_item, mentions_year
from src.core.domain.entities.software_instance.topic_operation import vocabulary_operation, vocabulary_topic
from pydantic import BaseModel, field_validator, HttpUrl, AnyUrl,  Field


def test_merge_same_name_and_type():
    parameters = {
        'name': 'TrimAl',
        'type': 'cmd',
    }
    other = instance(**parameters)
    other.version = ["1.4.2"]
    other.label = ["Trimal"]
    other.links = ["https://example.com/foo.py"]
    other.webpage = ["https://example.com"]
    other.download = ["https://github.com/user1/TrimAl/releases/download/v1.4.2/trimAl.zip"]
    other.repository = [{
        'url': "https://github.com/user1/TrimAl"
    }]
    other.operating_system = ["Linux", "Windows"]

    instance2 = instance(name="TrimAl", type="cmd")
    instance2.version = ["1.4.0"]
    instance2.label = ["TrimAl"]
    instance2.links = ["https://example.com/foo.py"]
    instance2.webpage = ["https://example.com"]
    instance2.download = ["https://github.com/user1/TrimAl/releases/download/v1.4.2/trimAl.zip"]
    instance2.repository = [{
        'url': "https://github.com/user1/TrimAl"
    }]
    instance2.operating_system = ["Linux"]
    
    instance2.merge(other)

    assert set(instance2.version) == set(["1.4.0", "1.4.2"])
    assert set(instance2.label) == set(["TrimAl", "Trimal"])
    assert instance2.links == [AnyUrl("https://example.com/foo.py")]
    assert instance2.webpage == [AnyUrl("https://example.com")]
    assert instance2.download == [AnyUrl("https://github.com/user1/TrimAl/releases/download/v1.4.2/trimAl.zip")]
    assert instance2.repository == [repository_item(url="https://github.com/user1/TrimAl")]


# ------------------------------------------------------------
# MERGE REPOSITORY 
# ------------------------------------------------------------

# Define the test function with parameters
@pytest.mark.parametrize("parameters_first, parameters_second, expected", [
    # Test case 1
    (
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'repository': [{'url': "https://github.com/user1/TrimAl"}]
        },
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'repository': [{'url': "https://github.com/organization1/TrimAl"}]
        },
        [
            repository_item(url="https://github.com/user1/TrimAl"),
            repository_item(url="https://github.com/organization1/TrimAl")
        ]
    ),
    # Test case 2
    (
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'repository': [
                {'url': "https://github.com/user1/TrimAl"},
                {'url': "https://gitlab.com/user1/TrimAl"}
            ]
        },
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'repository': [
                {'url': "https://gitlab.com/user1/TrimAl"}
            ]
        },
        [
            repository_item(url="https://github.com/user1/TrimAl"),
            repository_item(url="https://gitlab.com/user1/TrimAl")
        ]
    ),
    # Test case 3
    (
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'repository': [
                {'url': "https://github.com/user1/TrimAl"},
                {'url': "https://gitlab.com/user1/TrimAl"}
            ]
        },
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'repository': [
                {'url': "https://gitlab.com/organization/TrimAl"}
            ]
        },
        [
            repository_item(url="https://github.com/user1/TrimAl"),
            repository_item(url="https://gitlab.com/user1/TrimAl"),
            repository_item(url="https://gitlab.com/organization/TrimAl")
        ]
    )

])
def test_merge_same_type_name_different_repositories(parameters_first, parameters_second, expected):
    first = instance(**parameters_first)
    second = instance(**parameters_second)

    first.merge(second)

    assert first.repository == expected



# ------------------------------------------------------------
# OPERATING SYSTEMS
# ------------------------------------------------------------

@pytest.mark.parametrize("parameters_first, parameters_second, expected", [
    (
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'operating_system': ["Linux"]
        },
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'operating_system': ["Windows"]
        },
        [operating_systems.Linux, operating_systems.Windows]
    ),
    (
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'operating_system': ["Linux"]
        },
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'operating_system': ["Linux"]
        },
        [operating_systems.Linux]
    ),
    (
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'operating_system': ["Linux"]
        },
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'operating_system': ["Mac"]
        },
        [operating_systems.Linux, operating_systems.macOS]
    )
])
def test_merge_same_type_name_operating_system(parameters_first, parameters_second, expected):
    first = instance(**parameters_first)
    second = instance(**parameters_second)

    first.merge(second)

    assert set(first.operating_system) == set(expected)

#--------------------------------------------------------
#    SOURCE CODE
#--------------------------------------------------------
@pytest.mark.parametrize("parameters_first, parameters_second, expected", [
    (
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'source_code': ["https://github.com/user1/TrimAl/tree/master"]
        },
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'source_code': []
        },
        [AnyUrl("https://github.com/user1/TrimAl/tree/master")]
    ),
    (
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'source_code': []
        },
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'source_code': [
                "https://github.com/user1/TrimAl/tree/master", 
                "https://biocoductor.org/TrimAl"
                ]
        },
        [
            AnyUrl("https://github.com/user1/TrimAl/tree/master"),
            AnyUrl("https://biocoductor.org/TrimAl")
        ]
    ),
    (
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'source_code': ["https://biocoductor.org/TrimAl"]
        },
        {
            'name': 'TrimAl',
            'type': 'cmd',
            'source_code': [
                "https://github.com/user1/TrimAl/tree/master", 
                "https://biocoductor.org/TrimAl"
                ]
        },
        [
            AnyUrl("https://github.com/user1/TrimAl/tree/master"),
            AnyUrl("https://biocoductor.org/TrimAl")
        ]
    )
])
def test_merge_same_type_name_source_code(parameters_first, parameters_second, expected):
    first = instance(**parameters_first)
    second = instance(**parameters_second)

    first.merge(second)

    assert set(first.source_code) == set(expected)


#--------------------------------------------------------
#    INPUT
#--------------------------------------------------------

@pytest.mark.parametrize("parameters_first, parameters_second, expected", [
    (
        {
            'name': 'Software A',
            'input': [
                data_format(vocabulary="EDAM", term="Sequence format", uri="http://edamontology.org/format_1929",
                            datatype=data_type(vocabulary="EDAM", term="Nucleotide sequence", uri="http://edamontology.org/data_0006"))
            ]
        },
        {
            'name': 'Software A',
            'input': [
                data_format(vocabulary="EDAM", term="Sequence format", uri="http://edamontology.org/format_1929",
                            datatype=data_type(vocabulary="EDAM", term="Nucleotide sequence", uri="http://edamontology.org/data_0006"))
            ]
        },
        [
            data_format(vocabulary="EDAM", term="Sequence format", uri="http://edamontology.org/format_1929",
                        datatype=data_type(vocabulary="EDAM", term="Nucleotide sequence", uri="http://edamontology.org/data_0006"))
        ]
    ),
    (
        {
            'name': 'Software B',
            'input': [
                data_format(vocabulary="EDAM", term="Text format", uri="http://edamontology.org/format_2330")
            ]
        },
        {
            'name': 'Software B',
            'input': [
                data_format(vocabulary="EDAM", term="Sequence format", uri="http://edamontology.org/format_1929")
            ]
        },
        [
            data_format(vocabulary="EDAM", term="Text format", uri="http://edamontology.org/format_2330"),
            data_format(vocabulary="EDAM", term="Sequence format", uri="http://edamontology.org/format_1929")
        ]
    ),
    (
        {
            'name': 'Software C',
            'input': [
                data_format(term="txt")
            ]
        },
        {
            'name': 'Software C',
            'input': [
                data_format(term="plain text format (unformatted)")
            ]
        },
        [
            data_format(vocabulary="EDAM", term="Textual format", uri="http://edamontology.org/format_2330")
        ]
    )
])
def test_merge_input_data_formats(parameters_first, parameters_second, expected):
    first = instance(**parameters_first)
    second = instance(**parameters_second)

    first.merge(second)

    # correct uris

    assert first.input == expected


# ------------------------------------------------------------
#    OUTPUT
# ------------------------------------------------------------
@pytest.mark.parametrize("parameters_first, parameters_second, expected", [
    (
        {
            'name': 'Software A',
            'output': [
                data_format(vocabulary="EDAM", term="Text format", uri="http://edamontology.org/format_2333")
            ]
        },
        {
            'name': 'Software A',
            'output': [
                data_format(vocabulary="EDAM", term="Text format", uri="http://edamontology.org/format_2333")
            ]
        },
        [
            data_format(vocabulary="EDAM", term="Text format", uri="http://edamontology.org/format_2333")
        ]
    ),
    (
        {
            'name': 'Software B',
            'output': [
                data_format(vocabulary="EDAM", term="Sequence format", uri="http://edamontology.org/format_1929")
            ]
        },
        {
            'name': 'Software B',
            'output': [
                data_format(vocabulary="EDAM", term="Sequence format", uri="http://edamontology.org/format_1929",
                            datatype=data_type(vocabulary="EDAM", term="Nucleotide sequence", uri="http://edamontology.org/data_0017"))
            ]
        },
        [
            data_format(vocabulary="EDAM", term="Sequence format", uri="http://edamontology.org/format_1929",
                        datatype=data_type(vocabulary="EDAM", term="Nucleotide sequence", uri="http://edamontology.org/data_0017"))
        ]
    ),
    (
        {
            'name': 'Software C',
            'output': [
                data_format(vocabulary="EDAM", term="FASTA format", uri="http://edamontology.org/format_1930")
            ]
        },
        {
            'name': 'Software C',
            'output': [
                data_format(vocabulary="EDAM", term="Text format", uri="http://edamontology.org/format_2333"),
                data_format(vocabulary="EDAM", term="FASTA format", uri="http://edamontology.org/format_1930")
            ]
        },
        [
            data_format(vocabulary="EDAM", term="Text format", uri="http://edamontology.org/format_2333"),
            data_format(vocabulary="EDAM", term="FASTA format", uri="http://edamontology.org/format_1930")
        ]
    )
])
def test_merge_output_data_formats(parameters_first, parameters_second, expected):
    first = instance(**parameters_first)
    second = instance(**parameters_second)

    first.merge(second)

    # Convert to tuples for comparison to handle unhashable types
    def format_to_tuple(fmt):
        return (fmt.vocabulary, fmt.term, fmt.uri, fmt.datatype.vocabulary if fmt.datatype else None, fmt.datatype.term if fmt.datatype else None, fmt.datatype.uri if fmt.datatype else None)

    assert set(map(format_to_tuple, first.output)) == set(map(format_to_tuple, expected))


# ------------------------------------------------------------
#     Documentation
# ------------------------------------------------------------
@pytest.mark.parametrize("parameters_first, parameters_second, expected", [
    (
        # Test case 1: Identical documentation items
        {
            'name': 'Software A',
            'documentation': [
                documentation_item(type='general', url="http://example.com/doc1", content="Basic content")
            ]
        },
        {
            'name': 'Software A',
            'documentation': [
                documentation_item(type='general', url="http://example.com/doc1", content="Basic content")
            ]
        },
        [
            documentation_item(type='general', url="http://example.com/doc1", content="Basic content")
        ]
    ),
    (
        # Test case 2: Different documentation items
        {
            'name': 'Software B',
            'documentation': [
                documentation_item(type='general', url="http://example.com/doc1", content="Basic content")
            ]
        },
        {
            'name': 'Software B',
            'documentation': [
                documentation_item(type='installation', url="http://example.com/doc2", content="Installation guide")
            ]
        },
        [
            documentation_item(type='general', url="http://example.com/doc1", content="Basic content"),
            documentation_item(type='installation', url="http://example.com/doc2", content="Installation guide")
        ]
    ),
    (
        # Test case 3: Overlapping documentation with different content
        {
            'name': 'Software C',
            'documentation': [
                documentation_item(type='general', url="http://example.com/doc1", content="Basic content")
            ]
        },
        {
            'name': 'Software C',
            'documentation': [
                documentation_item(type='general', url="http://example.com/doc1", content="Updated basic content")
            ]
        },
        [
            documentation_item(type='general', url="http://example.com/doc1", content="Updated basic content")
        ]
    ),
    (
        # Test case 4: One has empty documentation
        {
            'name': 'Software D',
            'documentation': []
        },
        {
            'name': 'Software D',
            'documentation': [
                documentation_item(type='installation', url="http://example.com/doc2", content="Installation guide")
            ]
        },
        [
            documentation_item(type='installation', url="http://example.com/doc2", content="Installation guide")
        ]
    ),
    (
        # Test case 5: Both have empty documentation
        {
            'name': 'Software E',
            'documentation': []
        },
        {
            'name': 'Software E',
            'documentation': []
        },
        []
    ),
])
def test_merge_documentation(parameters_first, parameters_second, expected):
    first = instance(**parameters_first)
    second = instance(**parameters_second)

    first.merge(second)

    # Convert to tuples for comparison since documentation_item might be unhashable
    def doc_to_tuple(doc):
        return (doc.type, doc.url, doc.content)

    assert set(map(doc_to_tuple, first.documentation)) == set(map(doc_to_tuple, expected))


# ------------------------------------------------------------
#     LICENSE
# ------------------------------------------------------------

@pytest.mark.parametrize("parameters_first, parameters_second, expected", [
    (
        # Test case 1: Identical licenses
        {
            'name': 'Software A',
            'license': [
                license_item(name='MIT', url="http://example.com/MIT")
            ]
        },
        {
            'name': 'Software A',
            'license': [
                license_item(name='MIT', url="http://example.com/MIT")
            ]
        },
        [
            license_item(name='MIT', url="http://example.com/MIT")
        ]
    ),
    (
        # Test case 2: Different licenses
        {
            'name': 'Software B',
            'license': [
                license_item(name='MIT', url="http://example.com/MIT")
            ]
        },
        {
            'name': 'Software B',
            'license': [
                license_item(name='Apache-2.0', url="http://example.com/Apache")
            ]
        },
        [
            license_item(name='MIT', url="http://example.com/MIT"),
            license_item(name='Apache-2.0', url="http://example.com/Apache")
        ]
    ),
    (
        # Test case 3: Overlapping licenses with different URLs
        {
            'name': 'Software C',
            'license': [
                license_item(name='MIT', url="http://example.com/MIT")
            ]
        },
        {
            'name': 'Software C',
            'license': [
                license_item(name='MIT', url=None)
            ]
        },
        [
            license_item(name='MIT', url="http://example.com/MIT")
        ]
    ),
])
def test_merge_licenses(parameters_first, parameters_second, expected):
    first = instance(**parameters_first)
    second = instance(**parameters_second)

    first.merge(second)

    # Convert to tuples for comparison since license_item might be unhashable
    def license_to_tuple(lic):
        return (lic.name, lic.url)

    assert set(map(license_to_tuple, first.license)) == set(map(license_to_tuple, expected))


# ------------------------------------------------------------
# TERMS OF USE 
# ------------------------------------------------------------

@pytest.mark.parametrize("termsUse_self, termsUse_other, expected", [
    # Test case 1: self.termsUse is True, other.termsUse is False
    (True, False, True),
    
    # Test case 2: self.termsUse is False, other.termsUse is True
    (False, True, True),
    
    # Test case 3: self.termsUse is False, other.termsUse is False
    (False, False, False),
    
    # Test case 4: self.termsUse is True, other.termsUse is True
    (True, True, True)    
])

def test_merge_termsUse(termsUse_self, termsUse_other, expected):
    # Assuming that SoftwareInstance has an attribute 'termsUse' and a method 'merge'
    instance_self = instance(name='foo',termsUse=termsUse_self)
    instance_other = instance(name='foo',termsUse=termsUse_other)
    
    # Perform the merge
    instance_self.merge(instance_other)
    
    # Check the result
    assert instance_self.termsUse == expected


# ------------------------------------------------------------
# AUTHORS 
# ------------------------------------------------------------

@pytest.mark.parametrize("parameters_first, parameters_second, expected", [
    (
        # Test case 1: Identical contributors
        {
            'name': 'Software A',
            'authors': [
                contributor(name='John Doe', email='john.doe@example.com', maintainer=True)
            ]
        },
        {
            'name': 'Software A',
            'authors': [
                contributor(name='John Doe', email='john.doe@example.com', maintainer=True)
            ]
        },
        [
            contributor(name='John Doe', email='john.doe@example.com', maintainer=True)
        ]
    ),
    (
        # Test case 2: Different contributors
        {
            'name': 'Software B',
            'authors': [
                contributor(name='John Doe', email='john.doe@example.com', maintainer=True)
            ]
        },
        {
            'name': 'Software B',
            'authors': [
                contributor(name='Jane Smith', email='jane.smith@example.com', maintainer=False)
            ]
        },
        [
            contributor(name='John Doe', email='john.doe@example.com', maintainer=True),
            contributor(name='Jane Smith', email='jane.smith@example.com', maintainer=False)
        ]
    ),
    (
        # Test case 3: Overlapping contributors with different details
        {
            'name': 'Software C',
            'authors': [
                contributor(name='John Doe', email='john.doe@example.com', maintainer=True)
            ]
        },
        {
            'name': 'Software C',
            'authors': [
                contributor(name='John Doe', email=None, maintainer=False)
            ]
        },
        [
            contributor(name='John Doe', email='john.doe@example.com', maintainer=True)
        ]
    ),
])
def test_merge_authors(parameters_first, parameters_second, expected):
    first = instance(**parameters_first)
    second = instance(**parameters_second)

    first.merge(second)

    # Convert to tuples for comparison since contributor might be unhashable
    def author_to_tuple(author):
        return (author.name, author.email, author.maintainer, author.url, author.orcid)

    assert set(map(author_to_tuple, first.authors)) == set(map(author_to_tuple, expected))


# ------------------------------------------------------------
# MERGE PUBLICATIONS
# ------------------------------------------------------------ 
@pytest.mark.parametrize("parameters_first, parameters_second, expected", [
    (
        # Test case 1: Same DOI, different citation counts and years
        {
            'name': 'Software A',
            'publication': [
                publication_item(doi="10.1234/example.doi", cit_count=10, year=2020, title="Title A")
            ]
        },
        {
            'name': 'Software A',
            'publication': [
                publication_item(doi="10.1234/example.doi", cit_count=15, year=2020, title="Title A")
            ]
        },
        [
            publication_item(doi="10.1234/example.doi", cit_count=15, year=2020, title="Title A")
        ]
    ),
    (
        # Test case 2: Different publications
        {
            'name': 'Software B',
            'publication': [
                publication_item(doi="10.1234/example.doi", cit_count=10, year=2020, title="Title A")
            ]
        },
        {
            'name': 'Software B',
            'publication': [
                publication_item(pmcid="PMC1234567", cit_count=5, year=2019, title="Title B")
            ]
        },
        [
            publication_item(doi="10.1234/example.doi", cit_count=10, year=2020, title="Title A"),
            publication_item(pmcid="PMC1234567", cit_count=5, year=2019, title="Title B")
        ]
    ),
    (
        # Test case 3: Overlapping publications with different references and citations
        {
            'name': 'Software C',
            'publication': [
                publication_item(doi="10.1234/example.doi", refs=[mentions_year(year=2020, count="5")], ref_count=5, title="Title A", cit_count=8)
            ]
        },
        {
            'name': 'Software C',
            'publication': [
                publication_item(doi="10.1234/example.doi", refs=[mentions_year(year=2020, count="10")], ref_count=10, title="Title A", cit_count=12)
            ]
        },
        [
            publication_item(doi="10.1234/example.doi", refs=[mentions_year(year=2020, count="10")], ref_count=10, title="Title A", cit_count=12)
        ]
    ),
])
def test_merge_publications(parameters_first, parameters_second, expected):
    first = instance(**parameters_first)
    second = instance(**parameters_second)

    first.merge(second)

    # Convert to tuples for comparison since publication_item might be unhashable
    def pub_to_tuple(pub):
        return (pub.doi, pub.pmcid, pub.pmid, pub.cit_count, pub.year, pub.ref_count, pub.title)

    assert set(map(pub_to_tuple, first.publication)) == set(map(pub_to_tuple, expected))

# ------------------------------------------------------------
# MERGE PROGRAMMING LANGUAGES
# ------------------------------------------------------------

@pytest.mark.parametrize("languages_self, languages_other, expected", [
    # Test case 1: Both instances have the same languages
    (["Python", "JavaScript"], ["Python", "JavaScript"], ["Python", "JavaScript"]),

    # Test case 2: One instance has additional languages
    (["Python", "JavaScript"], ["Java", "C++"], ["Python", "JavaScript", "Java", "C++"]),

    # Test case 3: Both instances have different languages
    (["Python"], ["Ruby", "Go"], ["Python", "Ruby", "Go"]),

    # Test case 4: One instance has no languages
    (["Python", "JavaScript"], [], ["Python", "JavaScript"]),

    # Test case 5: Both instances have no languages
    ([], [], []),

    # Test case 6: Both instances have some overlapping languages
    (["Python", "JavaScript"], ["JavaScript", "Go"], ["Python", "JavaScript", "Go"]),
])

def test_merge_languages(languages_self, languages_other, expected):
    instance_self = instance(name="Instance A", languages=languages_self)
    instance_other = instance(name="Instance B", languages=languages_other)

    # Perform the merge
    instance_self.languages = list(set(instance_self.languages + instance_other.languages))

    # Ensure the result is correct, ignoring order
    assert set(instance_self.languages) == set(expected)

# ------------------------------------------------------------
# MERGE CITATION 
# ------------------------------------------------------------
def sort_citation_authors(citation):
    """
    Helper function to sort the authors in a citation dictionary.
    """
    if 'author' in citation and isinstance(citation['author'], list):
        citation['author'] = sorted(citation['author'])
    return citation

def sort_citations(citations):
    """
    Helper function to sort citations by a key and sort authors within each citation.
    """
    return sorted([sort_citation_authors(cit) for cit in citations], key=lambda x: (x.get('title', ''), x.get('year', ''), x.get('DOI', '')))

@pytest.mark.parametrize("citations_self, citations_other, expected", [
    # Test case 1: Identical citations
    (
        [{"title": "Software A", "year": "2022", "DOI": "10.1234/example.doi"}],
        [{"title": "Software A", "year": "2022", "DOI": "10.1234/example.doi"}],
        [{"title": "Software A", "year": "2022", "DOI": "10.1234/example.doi"}]
    ),

    # Test case 2: Different citations
    (
        [{"title": "Software A", "year": "2022", "DOI": "10.1234/example.doi"}],
        [{"title": "Software B", "year": "2023", "DOI": "10.5678/another.doi"}],
        [
            {"title": "Software A", "year": "2022", "DOI": "10.1234/example.doi"},
            {"title": "Software B", "year": "2023", "DOI": "10.5678/another.doi"}
        ]
    ),

    # Test case 3: Overlapping citations with different details
    (
        [{"title": "Software A", "year": "2022", "DOI": "10.1234/example.doi", "author": ["Author A"]}],
        [{"title": "Software A", "year": "2022", "DOI": "10.1234/example.doi", "author": ["Author B"]}],
        [{"title": "Software A", "year": "2022", "DOI": "10.1234/example.doi", "author": ["Author A", "Author B"]}]
    ),

    # Test case 4: Citations with missing fields
    (
        [{"title": "Software A", "year": "2022", "DOI": "10.1234/example.doi"}],
        [{"title": "Software A", "year": "2022"}],
        [{"title": "Software A", "year": "2022", "DOI": "10.1234/example.doi"}]
    ),

    # Test case 5: Citations with the same title but different years
    (
        [{"title": "Software A", "year": "2021", "DOI": "10.1234/example.doi"}],
        [{"title": "Software A", "year": "2022", "DOI": "10.1234/example.doi"}],
        [
            {"title": "Software A", "year": "2021", "DOI": "10.1234/example.doi"},
            {"title": "Software A", "year": "2022", "DOI": "10.1234/example.doi"}
        ]
    ),
])
def test_merge_citations(citations_self, citations_other, expected):
    instance_self = instance(name="Instance A", citation=citations_self)
    instance_other = instance(name="Instance A", citation=citations_other)

    # Perform the merge
    instance_self.merge(instance_other)

    # Ensure the result is correct
    assert sort_citations(instance_self.citation) == sort_citations(expected)

# ------------------------------------------------------------
# MERGE OPERATIONS 
# ------------------------------------------------------------
@pytest.mark.parametrize("ops_self, ops_other, expected", [
    # Test case 1: Identical operations
    (
        [vocabulary_operation(vocabulary='EDAM', term='Sequence alignment', uri='http://edamontology.org/operation_0292')],
        [vocabulary_operation(vocabulary='EDAM', term='Sequence alignment', uri='http://edamontology.org/operation_0292')],
        [vocabulary_operation(vocabulary='EDAM', term='Sequence alignment', uri='http://edamontology.org/operation_0292')]
    ),
    # Test case 2: Different operations
    (
        [vocabulary_operation(vocabulary='EDAM', term='Sequence alignment', uri='http://edamontology.org/operation_0292')],
        [vocabulary_operation(vocabulary='EDAM', term='Phylogenetic analysis', uri='http://edamontology.org/operation_0324')],
        [
            vocabulary_operation(vocabulary='EDAM', term='Sequence alignment', uri='http://edamontology.org/operation_0292'),
            vocabulary_operation(vocabulary='EDAM', term='Phylogenetic analysis', uri='http://edamontology.org/operation_0324')
        ]
    ),
])
def test_merge_operations(ops_self, ops_other, expected):
    instance_self = instance(name="Instance A", operations=ops_self)
    instance_other = instance(name="Instance A", operations=ops_other)

    # Perform the merge
    instance_self.merge(instance_other)

    # Ensure the result is correct
    assert instance_self.operations == expected


# ------------------------------------------------------------
# MERGE TOPICS
# ------------------------------------------------------------
@pytest.mark.parametrize("topics_self, topics_other, expected", [
    # Test case 1: Identical topics
    (
        [vocabulary_topic(vocabulary='EDAM', term='Genomics', uri='http://edamontology.org/topic_1234')],
        [vocabulary_topic(vocabulary='EDAM', term='Genomics', uri='http://edamontology.org/topic_1234')],
        [vocabulary_topic(vocabulary='EDAM', term='Genomics', uri='http://edamontology.org/topic_1234')]
    ),
    # Test case 2: Different topics
    (
        [vocabulary_topic(vocabulary='EDAM', term='Genomics', uri='http://edamontology.org/topic_1234')],
        [vocabulary_topic(vocabulary='EDAM', term='Proteomics', uri='http://edamontology.org/topic_5678')],
        [
            vocabulary_topic(vocabulary='EDAM', term='Genomics', uri='http://edamontology.org/topic_1234'),
            vocabulary_topic(vocabulary='EDAM', term='Proteomics', uri='http://edamontology.org/topic_5678')
        ]
    ),
])
def test_merge_topics(topics_self, topics_other, expected):
    instance_self = instance(name="Instance A", topics=topics_self)
    instance_other = instance(name="Instance A", topics=topics_other)

    # Perform the merge
    instance_self.merge(instance_other)

    # Ensure the result is correct
    assert instance_self.topics == expected
