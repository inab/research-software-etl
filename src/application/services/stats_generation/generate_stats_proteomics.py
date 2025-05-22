from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter

from src.application.services.stats_generation.trends.licenses import licenses_stats
from src.application.services.stats_generation.trends.versioning import semantic_versioning
from src.application.services.stats_generation.trends.version_control import version_control

from src.application.services.stats_generation.data.counts_source import count_tools_per_source, count_tools
from src.application.services.stats_generation.data.features import features_overview
from src.application.services.stats_generation.data.metadata_completeness import features_cummulative, features_xy
from src.application.services.stats_generation.data.type import count_types_tools

from src.application.services.stats_generation.FAIR.fair_calculation import compute_fair_distributions


#collections = ['RIS3CAT VEIS', 'ELIXIR-ES', 'PerMedCoE', 'IMPaCT-Data', 'tools']
#collections = ['ELIXIR-ES', 'PerMedCoE', 'IMPaCT-Data', ]
#collections = ['tools']

collections = ['Proteomics']



for collection in collections:

    print(f'Processing collection: {collection}')

    if collection == 'tools':
        query = {}
    
    else:
        query = {'data.tags': collection}

    tools = mongo_adapter.fetch_entries("toolsDev", query)

    #features_overview(tools, collection=collection)

    
    compute_fair_distributions(tools, collection=collection)
    


        
        

        
