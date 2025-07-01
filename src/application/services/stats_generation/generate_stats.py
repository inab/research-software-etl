from dotenv import load_dotenv
import os

load_dotenv(dotenv_path='/Users/evabsc/projects/software-observatory/research-software-etl/.env', override=True)


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


#collections = ['RIS3CAT VEIS', 'ELIXIR-ES', 'PerMedCoE', 'IMPaCT-Data', 'Proteomics','tools']
#collections = ['ELIXIR-ES', 'PerMedCoE', 'IMPaCT-Data', ]
#collections = ['tools']
#collections = ['BioExcel', '3D-BioInfo', 'EUCAIM']
collections = ['eucaim']


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
    
    print('Version control done')
    
    
    count_tools_per_source(tools, collection=collection)
    count_tools(tools, collection=collection)
    version_control(tools, collection=collection)
    coverage_sources(tools, collection=collection)
    features_overview(tools, collection=collection)
    features_cummulative(tools, collection=collection)
    features_xy(tools, collection=collection)
    count_types_tools(tools, collection=collection)
    compute_fair_distributions(tools, collection=collection)
    publications_journals_IF(collection=collection)
    dependencies(tools, collection=collection)


        
        

        
