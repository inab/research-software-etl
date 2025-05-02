import copy

# original conflict from real case
original_key = "ale/cmd"

original_dis_one = {
                "name": "ale",
                "types": "cmd",
                "source": [
                    "biotools"
                ],
                "description": "Automated label extraction from GEO metadata.",
                "repository": [],
                "webpage": [
                    "github.com/wrenlab/label-extraction"
                ],
                "id": "biotools/ale/cmd/None"
            }

original_remaining_one = {
                "name": "ale",
                "types": "cmd",
                "source": [
                    "bioconda_recipes"
                ],
                "description": "ALE: Assembly Likelihood Estimator.",
                "repository": [
                    "github.com/sc932/ALE"
                ],
                "webpage": [
                    "github.com/sc932/ALE"
                ],
                "id": "bioconda_recipes/ale/cmd/20180904"
            }

original_remaining_two = {
                "name": "ale-core",
                "types": "cmd",
                "source": [
                    "bioconda_recipes"
                ],
                "description": "This package is designed to hold the core scoring functionality of ALE without the 10+ year old supplementary python plotting scripts.",
                "repository": [
                    "github.com/sc932/ALE"
                ],
                "webpage": [
                    "github.com/sc932/ALE"
                ],
                "id": "bioconda_recipes/ale-core/cmd/20220503"
            }

original_remaining_three = {
                "name": "ALE",
                "types": None,
                "source": [
                    "github"
                ],
                "description": "Assembly Likelihood Estimator.",
                "repository": [
                    "github.com/sc932/ALE"
                ],
                "webpage": [],
                "id": "github/ALE/None/None"
            }


original_conflict_one_two = {
        "disconnected": [
            copy.deepcopy(original_dis_one)
        ],
        "remaining": [
            copy.deepcopy(original_remaining_one),
            copy.deepcopy(original_remaining_two)
        ]
    }

original_conflict_one_three = {
        "disconnected": [
            copy.deepcopy(original_dis_one)
        ],
        "remaining": [
            copy.deepcopy(original_remaining_one),
            copy.deepcopy(original_remaining_two),
            copy.deepcopy(original_remaining_three)
        ]
    }


original_conflict_two_one = {
    'disconnected': [
        copy.deepcopy(original_dis_one),
        copy.deepcopy(original_remaining_one)
    ],
    'remaining': [
       copy.deepcopy(original_remaining_two)
    ]
}

original_conflict_two_zero = {
    'disconnected': [
        copy.deepcopy(original_dis_one),
        copy.deepcopy(original_remaining_one)
    ],
    'remaining': []
}

original_conflict_zero_two = {
    'disconnected': [],
    'remaining': [
        copy.deepcopy(original_remaining_one),
        copy.deepcopy(original_remaining_two)
    ]
}

conflicts_blocks_sets = [
    {"ale/cmd" : original_conflict_one_two},
    {"ale/cmd" : original_conflict_one_three},
    {"ale/cmd" : original_conflict_two_one},
    {"ale/cmd" : original_conflict_two_zero},
    {"ale/cmd" : original_conflict_zero_two}
]