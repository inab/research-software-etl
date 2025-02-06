from functools import wraps
import os
import time
import logging
from dotenv import load_dotenv
from datetime import datetime

# import pymongo
from pymongo import MongoClient
from pymongo.collection import Collection

# --------------------------------------------
# Constants 
# --------------------------------------------
global webTypes
webTypes = ['rest', 'web', 'app', 'suite', 'workbench', 'db', 'soap', 'sparql']

# Labels of sources accross FAIRsoft pacakage. Must be consistent!!!! 
# Present in:
# 1.- 'sources' field in `instance`` objects (and anywhere they appear in code) 
# 2.- toolGenerators in FAIRsoft.meta_transformers
# if labels change in one place, they must change in the others for everythong to keep working

sources_labels = {
    'BIOCONDUCTOR':'bioconductor',
    'BIOCONDA':'bioconda',
    'BIOTOOLS':'biotools',
    'TOOLSHED':'toolshed',
    'GALAXY_METADATA':'galaxy_metadata',
    'SOURCEFORGE': 'sourceforge',
    'GALAXY_EU': 'galaxy',
    'OPEB_METRICS':'opeb_metrics',
    'BIOCONDA_RECIPES':'bioconda_recipes',
    'BIOCONDA_CONDA':'bioconda_conda',
    'REPOSITORIES': 'repository',
    'GITHUB': 'github',
    'BITBUCKET': 'bitbucket'
}

def timeit(func):
    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        print(f'Function {func.__name__}{args} {kwargs} Took {total_time:.4f} seconds')
        return result
    return timeit_wrapper


