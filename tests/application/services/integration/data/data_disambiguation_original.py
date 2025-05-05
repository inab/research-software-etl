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


expected_one_two = {
    'merged_entries': ['bioconda_recipes/ale/cmd/20180904', 'bioconda_recipes/ale-core/cmd/20220503'],
    'unmerged_entries': ['biotools/ale/cmd/None'],
    'resolution': 'partial',
    'notes': 'Caution: merged entries have different names — may be distinct software.'
}

expected_one_three = {
    'merged_entries': ['bioconda_recipes/ale/cmd/20180904', 'bioconda_recipes/ale-core/cmd/20220503', 'github/ALE/None/None'],
    'unmerged_entries': ['biotools/ale/cmd/None'],
    'resolution': 'partial',
    'notes': 'Caution: merged entries have different names — may be distinct software.'
}

expected_two_one = {
    'merged_entries': ['bioconda_recipes/ale-core/cmd/20220503'],
    'unmerged_entries': ['biotools/ale/cmd/None', 'bioconda_recipes/ale/cmd/20180904'],
    'resolution': 'partial',
    'notes': None
}

expected_two_zero = {
    'merged_entries': ['biotools/ale/cmd/None'],
    'unmerged_entries': ['bioconda_recipes/ale/cmd/20180904'],
    'resolution': 'partial',
    'notes': None
}

expected_zero_two = {
    'merged_entries': ['bioconda_recipes/ale/cmd/20180904', 'bioconda_recipes/ale-core/cmd/20220503'],
    'unmerged_entries': [],
    'resolution': 'merged',
    'notes': 'All entries grouped heuristically or by shared metadata. No disambiguation needed. Caution: merged entries have different names — may be distinct software.'
}

expected = [
    expected_one_two,
    expected_one_three,
    expected_two_one,
    expected_two_zero,
    expected_zero_two
]

expected_heuristics = {
    '1000genomes_vcf2ped/web': {
        'merged_entries': ['biotools/1000genomes_vcf2ped/web/1'],
        'unmerged_entries': [],
        'resolution': 'no_conflict',
        'source': 'auto:no_conflict',
        'confidence_scores': {},
        'timestamp': '2025-04-28T15:00:00.000Z',
        'notes': 'All entries grouped heuristically or by shared metadata. No disambiguation needed.'
    },
    'mapcaller/cmd': {
        'merged_entries':['bioconda_recipes/mapcaller/cmd/0.9.9.41', 'biotools/mapcaller/cmd/None', 'github/MapCaller/None/v0.9.9.d'],
        'unmerged_entries': [],
        'resolution': 'no_conflict',
        'source': 'auto:no_conflict',
        'confidence_scores': {},
        'timestamp': '2025-04-28T15:00:00.000Z',
        'notes': 'All entries grouped heuristically or by shared metadata. No disambiguation needed. Caution: merged entries have different names — may be distinct software.'
    },
    'cvinspector/cmd': {
        'merged_entries': ['galaxy/cvinspector/cmd/2.3.0', 'galaxy_metadata/cvinspector/cmd/2.2.0', 'toolshed/cvinspector/cmd/2.2.0'],
        'unmerged_entries': [],
        'resolution': 'no_conflict',
        'source': 'auto:no_conflict',
        'confidence_scores': {},
        'timestamp': '2025-04-28T15:00:00.000Z',
        'notes': 'All entries grouped heuristically or by shared metadata. No disambiguation needed.'
    }
}