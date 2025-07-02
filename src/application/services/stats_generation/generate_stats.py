from dotenv import load_dotenv
import os

def generate_stats_for_collections(collections):
    from src.application.services.stats_generation.trends.licenses import licenses_stats
    from src.application.services.stats_generation.trends.versioning import semantic_versioning
    from src.application.services.stats_generation.trends.version_control import version_control
    from src.application.services.stats_generation.trends.publications import publications_journals_IF
    from src.application.services.stats_generation.data.counts_source import count_tools_per_source, count_tools
    from src.application.services.stats_generation.data.features import features_overview
    from src.application.services.stats_generation.data.metadata_completeness import features_cummulative, features_xy
    from src.application.services.stats_generation.data.type import count_types_tools
    from src.application.services.stats_generation.data.coverage import coverage_sources
    from src.application.services.stats_generation.FAIR.fair_calculation import compute_fair_distributions
    from src.application.services.stats_generation.trends.dependencies import dependencies
    from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter

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
        compute_fair_distributions(tools, collection=collection)
        print('Fair distributions done')
        publications_journals_IF(collection=collection)
        print('Publications journals IF done')
        dependencies(tools, collection=collection)
        print('Dependencies done')


# Default collections if run as a script
default_collections = ['eucaim']

if __name__ == "__main__":
    load_dotenv(dotenv_path='/Users/evabsc/projects/software-observatory/research-software-etl/.env', override=True)
    generate_stats_for_collections(default_collections)


        
        

        
