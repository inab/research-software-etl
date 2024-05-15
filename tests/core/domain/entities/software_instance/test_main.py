import pytest
from src.core.domain.entities.software_instance.main import instance, operating_systems
from src.core.domain.entities.software_instance.repository import repository_item
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

