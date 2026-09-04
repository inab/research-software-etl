import hashlib
import json
import time
import logging
from functools import wraps
from typing import Any
from pydantic import ValidationError

logger = logging.getLogger("rs-etl-pipeline")


def _canonicalize(value: Any) -> Any:
    """
    Rewrite ``value`` into a form whose JSON serialization does not depend on
    list order.

    Merged tool ``data`` is built through pydantic validators that call
    ``list(set(...))`` (``source_code``, ``description``, ...), so the order of
    those lists is not stable from one run to the next even when the content is
    identical. Sorting every list here makes the fingerprint order-insensitive:
    it flips only when the *set* of values changes, not when they are shuffled.

    The trade-off is that a change consisting solely of reordering a list (e.g.
    which ``version`` is listed first) is not seen as a change. FAIR indicators
    key on presence and counts rather than position, so this is acceptable.
    """
    if isinstance(value, dict):
        return {key: _canonicalize(val) for key, val in value.items()}
    if isinstance(value, list):
        canon = [_canonicalize(item) for item in value]
        return sorted(canon, key=lambda item: json.dumps(item, sort_keys=True, default=str))
    return value


def content_hash(data: dict) -> str:
    """
    A stable fingerprint of a record's ``data`` payload.

    Two records with the same content produce the same hash regardless of
    run-to-run list ordering, so a stage can tell whether a record actually
    changed since the previous run. Pure: no clock, no database, no
    iteration-order dependence.
    """
    payload = json.dumps(_canonicalize(data), sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

# --------------------------------------------
# Constants 
# --------------------------------------------
global webTypes
webTypes = ['rest', 'web', 'app', 'suite', 'workbench', 'db', 'soap', 'sparql']


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
    if isinstance(url, str):
        if 'github.com/' in url:
            if len(url.split('github.com/'))>1:
                end =  url.split('github.com/')[1]
                if len(end.split('/'))>=2:
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
    if isinstance(url, str):
        if 'gitlab.com/' in url:
            if len(url.split('gitlab.com/'))>1:
                end =  url.split('gitlab.com/')[1]
                if len(end.split('/'))>=2:
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
    if isinstance(url, str):
        if 'bitbucket.org/' in url:
            if len(url.split('bitbucket.org/'))>1:
                end =  url.split('bitbucket.org/')[1]
                if len(end.split('/'))>=2:
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
    if gitlab_repo:
        return { 'kind': 'gitlab', 'url': gitlab_repo}
    
    bitbucket_repo = is_bitbucket_repo(url)
    if bitbucket_repo:
        return { 'kind': 'bitbucket', 'url': bitbucket_repo}
    
    return None

def validate_and_filter(instance_cls, **data):
    """Validates data dictionary, keeping only valid fields."""
    try:
        # Validate the entire input data
        validated_instance = instance_cls(**data)
        return validated_instance  # Return the fully valid instance
    except ValidationError as e:
        # If validation fails, filter out invalid fields
        logger.warning(f"Could not validate the entire entry. Some fields will be excluded: {e}")
        for error in e.errors():
            logger.warning(f"Could not validate a filed. It will be excluded from the entry: {error}")
            invalid_field = error["loc"][0]  # Get the invalid field name
            data.pop(invalid_field, None)  # Remove the invalid field
        
        # Create a new instance with only valid fields
        return instance_cls(**data)