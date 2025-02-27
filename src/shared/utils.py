import time

from functools import wraps
from pydantic import ValidationError

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
def is_github_repo(url):
    '''
    Checks if the url is a github repository.
    - url: url to check
    '''
    if 'github.com' in url:
        end =  url.split('github.com/')[1]
        owner = end.split('/')[0]
        repo = end.split('/')[1]

        clean_repo = f"https://github.com/{owner}/{repo}"

        return clean_repo
        
    else:
        return None

def is_gitlab_repo(url):
    '''
    Checks if the url is a gitlab repository.
    - url: url to check
    '''
    if 'gitlab.com' in url:
        end =  url.split('gitlab.com/')[1]
        owner = end.split('/')[0]
        repo = end.split('/')[1]
        
        clean_repo = f"https://gitlab.com/{owner}/{repo}"

        return clean_repo
        
    else:
        return None
        
    
def is_bitbucket_repo(url):
    '''
    Checks if the url is a bitbucket repository.
    - url: url to check
    '''
    if 'bitbucket.org' in url:
        end =  url.split('bitbucket.org/')[1]
        owner = end.split('/')[0]
        repo = end.split('/')[1]
        
        clean_repo = f"https://bitbucket.org/{owner}/{repo}"
        return clean_repo
        
    else:
        return None

def is_repository(url):
    '''
    Checks if the url is a repository.
    - url: url to check
    '''
    gh_repo = is_github_repo(url)
    if gh_repo:
        return { 'kind': 'github', 'url': gh_repo}
    
    gitlab_repo = is_gitlab_repo(url)
    if gitlab_repo(url):
        return { 'kind': 'gitlab', 'url': gitlab_repo}
    
    bitbucket_repo = is_bitbucket_repo(url)
    if bitbucket_repo:
        return { 'kind': 'bitbucket', 'url': bitbucket_repo}
    
    return []

def validate_and_filter(instance_cls, **data):
    """Validates data dictionary, keeping only valid fields."""
    try:
        # Validate the entire input data
        validated_instance = instance_cls(**data)
        return validated_instance  # Return the fully valid instance
    except ValidationError as e:
        # If validation fails, filter out invalid fields
        for error in e.errors():
            invalid_field = error["loc"][0]  # Get the invalid field name
            data.pop(invalid_field, None)  # Remove the invalid field
        
        # Create a new instance with only valid fields
        return instance_cls(**data)