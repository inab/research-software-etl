"""
Application use case: orchestrate statistics generation for selected tool collections.

This module defines the application-level workflow that runs the complete
statistics-generation process over one or more selected tool collections.

Each collection identifier represents either the entire tools dataset or a
tag-based subset of tools. For every requested collection, the workflow fetches
the corresponding tool records and executes the available statistics services.

when to run:
- Every time the metadata collection is updated.
- AFTER the generation of FAIR scores so the FAIR scores distributions are up-to-date

"""

from dotenv import load_dotenv

def generate_stats_for_collections(collections):
    from application.services.stats_generation.trends.licenses import licenses_stats
    from application.services.stats_generation.trends.versioning import semantic_versioning
    from application.services.stats_generation.trends.version_control import version_control
    from application.services.stats_generation.trends.publications import publications_journals_IF
    from application.services.stats_generation.data.counts_source import count_tools_per_source, count_tools
    from application.services.stats_generation.data.features import features_overview
    from application.services.stats_generation.data.metadata_completeness import features_cummulative, features_xy
    from application.services.stats_generation.data.type import count_types_tools
    from application.services.stats_generation.data.coverage import coverage_sources
    from application.services.stats_generation.FAIR.fair_calculation import compute_fair_distributions
    from application.services.stats_generation.trends.dependencies import dependencies
    from application.services.stats_generation.trends.documentation import documentation
    from application.services.stats_generation.trends.formats import formats
    from infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


    for collection in collections:
        print(f'Processing collection: {collection}')

        if collection == 'tools':
            query = {}
        else:
            query = {'data.tags': collection}

        tools = mongo_adapter.fetch_entries("toolsDev", query)

        licenses_stats(tools, collection=collection)
        print('Licenses stats done')
        
        semantic_versioning(tools, collection=collection)
        print('Semantic versioning done')
        
        count_tools_per_source(tools, collection=collection)
        print('Count tools per source done')
        
        count_tools(tools, collection=collection)
        print('Count tools done')
        
        version_control(tools, collection=collection)
        print('Version control done')
        
        coverage_sources(tools, collection=collection)
        print('Coverage sources done')
        
        features_overview(tools, collection=collection)
        print('Features overview done')
        
        features_cummulative(tools, collection=collection)
        print('Features cummulative done')
        
        features_xy(tools, collection=collection)
        print('Features xy done')
        
        count_types_tools(tools, collection=collection)
        print('Count types tools done')
        
        dependencies(tools, collection=collection)
        print('Dependencies done')
        
        documentation(tools, collection=collection)
        print('Documentation done')
        
        formats(tools, collection=collection)
        print('Input and otput data formats done')

        publications_journals_IF(collection=collection)
        print('Publications journals IF done')


        


# Default collections if run as a script
default_collections = ['eucaim']

if __name__ == "__main__":
    load_dotenv(dotenv_path='/Users/evabsc/projects/software-observatory/research-software-etl/.env', override=True)
    generate_stats_for_collections(default_collections)


        
        

        
