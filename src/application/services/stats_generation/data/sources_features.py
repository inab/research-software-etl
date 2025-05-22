from datetime import datetime
from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


def build_features_dict(source):
    """
    Build a dictionary with features as keys and values as zeros.
    """
    i = 1
    features = {}
    for feature in all_features:
        if feature in source:
            features[feature] = i
        else:
            features[feature] = 0
        i += 1

    return features


bioconda = [
    "name",
    "type",
    "version",
    "source",
    "label",
    "description",
    "source_code",
    "download",
    "license",
    "documentation",
    "operating_system",
    "repository",
    "webpage",
    "dependencies",
    "authors",
    "publication",
]
bioconductor = [
            "name",
            "type",
            "version",
            "source",
            "label",
            "description",
            "license",
            "operating_system",
            "repository",
            "webpage",
            "dependencies",
            "authors",
            "publication",
            ]
biotools = [
            "name",
            "type",
            "version",
            "source",
            "label",
            "description",
            "license",
            "documentation",
            "operating_system",
            "repository",
            "webpage",
            "input",
            "output",
            "topics",
            "operations",
            "authors",
            "tags",
            "links",
            "publiction",
            "publication"
        ]
toolshed = ["name",
            "type",
            "version",
            "source",
            "label",
            "description",
            "documentation",
            "operating_system",
            "input",
            "test",
            "output",
            "repository",
            "dependencies",
            "publication",
            ]
galaxy = [
    "name",
    "type",
    "version",
    "label",
    "source",
    "description",
    "operating_systems",
    "webpage"
]
sourceforge = [
        "name",
        "version",
        "label",
        "source",
        "description",
        "operating_system",
        "repository",
        "webpage",
        "download",
        "license"
        ]
github = [
        "name",
        "source",
        "description",
        "type",
        "version",
        "label",
        "links",
        "webpage",
        "download",
        "repository",
        "operating_system",
        "documentation",
        "authors",
        "publications",
        "topics",
        "license"
    ]



all_features = [
    "name",
    "type",
    "version",
    "label",
    "description",
    "source_code",
    "download",
    "license",
    "documentation",
    "operating_system",
    "repository",
    "webpage",
    "input",
    "output",
    "dependencies",
    "test",
    "authors",
    "publication",
    "topics"
]



def get_features():
    result = [
        {
        "name": 'bioconda',
        "features": build_features_dict(bioconda),
        },
        {
            "name": "bioconductor",
            "features": build_features_dict(bioconductor),
        },
        {
            "name": "biotools",
            "features": build_features_dict(biotools),
        },
        {
            "name": "toolshed",
            "features": build_features_dict(toolshed),
        },
        {
            "name": "galaxy",
            "features": build_features_dict(galaxy),
        },
        {
            "name": "sourceforge",
            "features": build_features_dict(sourceforge),
        },
        {
            "name": "github",
            "features": build_features_dict(github),
        }
    ]

    data = {
        'variable': "features_dots",
        'version': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'data': result,
        'collection': 'tools'
    }

    mongo_adapter.insert_one("computationsDev", data)


if __name__ == "__main__":
    get_features()




