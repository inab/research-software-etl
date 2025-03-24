from src.application.use_cases.integration.data_integration import group_by_link 
from src.domain.models.software_instance import SoftwareInstance
from faker import Faker
from pydantic import AnyUrl

from src.application.use_cases.integration.data_integration import group_by_link 
from src.domain.models.software_instance.main import instance, software_types, operating_systems, data_sources

faker = Faker()

# Function to create a mock instance
def generate_mock_instance():
    return instance(
        name=faker.word(),
        type=faker.random_element(list(software_types)),
        version=[faker.random_element(["1.0", "2.0", "3.1"])],
        label=[faker.word().capitalize()],
        links=[AnyUrl("https://example.com")],
        operating_system=[faker.random_element(list(operating_systems))],
        source=[faker.random_element(list(data_sources))],
        description=[faker.sentence()],
        languages=[faker.random_element(["Python", "R", "C++"])],
    )

# Generate 3 mock instances
mock_instances = [generate_mock_instance() for _ in range(3)]



def test_group_by_link():
    
    # ---------- Input sets ----------
    # ----------   SET A    -----------
    mock_a_foo = [generate_mock_instance() for _ in range(3)]
    mock_a_bar = [generate_mock_instance() for _ in range(1)]
    set_a = [
       {
            'instances' :  mock_a_foo,
            'links' : ['link1', 'link2']
        },
        {
            'instances' : mock_a_bar,
            'links' : ['link3', 'link4']
        }
    ]

    # ----------   SET B    -----------
    mock_b_foo = [generate_mock_instance() for _ in range(3)]
    mock_b_bar = [generate_mock_instance() for _ in range(2)]
    set_b = [
        {
        'instances' : mock_b_foo,
        'links' : ['linkA', 'link2']
        },
        {
        'instances' :   mock_b_bar,
        'links' : ['linkB', 'linkC']
        }
    ]


    # ---------- Expected output ----------
    # ----------     SET A       ----------  
    expected_set_a = [
        {
            'instances' : mock_a_foo + mock_b_foo,
            'links' : ['link1', 'link2', 'linkA']
        },
        {
            'instances' : mock_a_bar,
            'links' : ['link3', 'link4']
        }
    ]

    # ----------   SET B    -----------
    expected_set_b = [
        {
            'instances' : mock_b_bar,
            'links' : ['linkB', 'linkC']
        }
    ]
        

    
    result_set_a, result_set_b = group_by_link(set_a, set_b)

    assert result_set_a == expected_set_a
    assert result_set_b == expected_set_b