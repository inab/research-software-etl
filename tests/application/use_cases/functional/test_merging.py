from bson import json_util
from bson import ObjectId
import copy
from src.application.use_cases.integration.merge_entries import convert_to_multi_type_instance, merge_instances
from src.domain.models.software_instance.main import software_types
test_entries = [
    {
        "_id": "biotools/ps2-v3/web/3.0",
        "created_at": "2025-03-25T15:23:37.221591",
        "created_by": "https://gitlab.bsc.es/None/None/-/commit/None",
        "created_logs": "local",
        "last_updated_at": "2025-03-25T15:23:37.221591",
        "updated_by": "https://gitlab.bsc.es/None/None/-/commit/None",
        "updated_logs": "local",
        "source": [
            {
            "collection": "alambiqueDev",
            "id": "biotools/ps2-v3/web/3.0",
            "source_url": None
            }
        ],
        "data": {
            "name": "ps2-v3",
            "type": "web",
            "version": ["3.0"],
            "publication": [ ObjectId("67c829fc10e2f3aa0b3b89d8")],
            
        }
    },
    {
        "_id": "biotools/ps2-v3/web/3.0",
        "created_at": "2025-03-25T15:23:37.221591",
        "created_by": "https://gitlab.bsc.es/None/None/-/commit/None",
        "created_logs": "local",
        "last_updated_at": "2025-03-25T15:23:37.221591",
        "updated_by": "https://gitlab.bsc.es/None/None/-/commit/None",
        "updated_logs": "local",
        "source": [
            {
            "collection": "alambiqueDev",
            "id": "biotools/foo/cmd/1.0",
            "source_url": None
            }
        ],
        "data": {
            "name": "ps2-v3",
            "type": "cmd",
            "version": ["1.0"],
            "publication": [ObjectId("67c8282b10e2f3aa0b3b79ba")],
        }
    },
    {
        "_id": "biotools/ps2-v3/web/3.0",
        "created_at": "2025-03-25T15:23:37.221591",
        "created_by": "https://gitlab.bsc.es/None/None/-/commit/None",
        "created_logs": "local",
        "last_updated_at": "2025-03-25T15:23:37.221591",
        "updated_by": "https://gitlab.bsc.es/None/None/-/commit/None",
        "updated_logs": "local",
        "source": [
            {
            "collection": "alambiqueDev",
            "id": "biotools/ps2-v3/cmd/1.0",
            "source_url": None
            }
        ],
        "data": {
            "name": "ps2-v3",
            "type": "web",
            "version": ["1.0"],
            "publication": [
                ObjectId("67c78b39d3b8acd1a2f9b1f1"),
                ObjectId("67c8282b10e2f3aa0b3b79ba")
            ],
        }
    },
]

def test_convert_to_multi_type_instance():
    
    # convert to multitype_instance
    instances = [convert_to_multi_type_instance(entry) for entry in copy.deepcopy(test_entries)]

    # check if type is a list
    print(f"Type of first instance: {instances[0].type}")
    assert isinstance(instances[0].type, list)

    print(f"Type of second instance: {instances[1].type}")
    assert isinstance(instances[1].type, list)

    print(f"Type of third instance: {instances[2].type}")
    assert isinstance(instances[2].type, list)

def test_merge_instances():
    # convert to multitype_instance
    instances = [convert_to_multi_type_instance(entry) for entry in copy.deepcopy(test_entries)]

    merged_instances = merge_instances(instances)
    print(f"Merged instance: {merged_instances}")

    print(f"Merged instance type: {merged_instances.type}")
    assert set(merged_instances.type) == set([software_types.web, software_types.cmd])

    print(f"Merged instance version: {merged_instances.version}")
    assert set(merged_instances.version) == set(['3.0', '1.0'])

    print(f"Merged instance publication: {merged_instances.publication}")
    assert set(merged_instances.publication) == set([
        ObjectId("67c829fc10e2f3aa0b3b89d8"),
        ObjectId("67c8282b10e2f3aa0b3b79ba"),
        ObjectId("67c78b39d3b8acd1a2f9b1f1")
    ])