"""
Application use case: orchestrate statistics generation for selected tool collections.

Each collection identifier is either the whole tools dataset or a tag-scoped
subset of it. For every requested collection the workflow fetches the matching
tools once and runs each statistics service over them.

when to run:
- Every time the metadata collection is updated.
- AFTER the generation of FAIR scores so the FAIR scores distributions are up-to-date
"""

from application.services.stats_generation.data.counts_source import (
    count_tools,
    count_tools_per_source,
)
from application.services.stats_generation.data.coverage import coverage_sources
from application.services.stats_generation.data.features import features_overview
from application.services.stats_generation.data.metadata_completeness import (
    features_cummulative,
    features_xy,
)
from application.services.stats_generation.data.type import count_types_tools
from application.services.stats_generation.FAIR.fair_distribution import (
    compute_fair_distributions,
)
from application.services.stats_generation.trends.dependencies import dependencies
from application.services.stats_generation.trends.documentation import documentation
from application.services.stats_generation.trends.formats import formats
from application.services.stats_generation.trends.licenses import licenses_stats
from application.services.stats_generation.trends.publications import (
    publications_journals_IF,
)
from application.services.stats_generation.trends.version_control import version_control
from application.services.stats_generation.trends.versioning import semantic_versioning
from infrastructure.db.repositories import Repositories


def generate_stats_for_collections(collections, repos: Repositories):
    """
    Run every statistics service over each requested collection.

    Services that only write take the computations repository; the two that read
    other collections as well take the whole bundle.
    """
    computations = repos.computations

    for collection in collections:
        print(f'Processing collection: {collection}')

        if collection == 'tools':
            tools = repos.tools.get_all()
        else:
            tools = repos.tools.find({'data.tags': collection})

        licenses_stats(tools, collection, computations)
        print('Licenses stats done')

        semantic_versioning(tools, collection, computations)
        print('Semantic versioning done')

        count_tools_per_source(tools, collection, computations)
        print('Count tools per source done')

        count_tools(tools, collection, computations)
        print('Count tools done')

        version_control(tools, collection, computations)
        print('Version control done')

        coverage_sources(tools, collection, computations)
        print('Coverage sources done')

        features_overview(tools, collection, computations)
        print('Features overview done')

        features_cummulative(tools, collection, computations)
        print('Features cummulative done')

        features_xy(tools, collection, computations)
        print('Features xy done')

        count_types_tools(tools, collection, computations)
        print('Count types tools done')

        dependencies(tools, collection, computations)
        print('Dependencies done')

        documentation(tools, collection, computations)
        print('Documentation done')

        formats(tools, collection, computations)
        print('Input and otput data formats done')

        publications_journals_IF(collection, repos)
        print('Publications journals IF done')

        compute_fair_distributions(collection, repos)
        print('FAIR distributions done')
