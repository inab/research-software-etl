from pydantic import BaseModel, HttpUrl, model_validator
from typing import List, Optional
from enum import Enum


class repository_kind(str, Enum):
    '''
    Class to represent a repository kind. These are the kinds normally found
    for the tools in the Life Sciences.
    '''
    github = 'github'
    bitbucket = 'bitbucket'
    sourceforge = 'sourceforge'
    gitlab = 'gitlab'
    bioconda = 'bioconda'
    bioconductor = 'bioconductor'


class repository_item(BaseModel):
    '''
    Class to represent a repository.
    '''
    url : HttpUrl
    kind : Optional[repository_kind] = None
    source_hasAnonymousAccess : Optional[bool] = None
    source_isDownloadRegistered : Optional[bool] = None
    source_isFree: Optional[bool] = None
    source_isRepoAccessible : Optional[bool] = None

    @model_validator(mode="before")
    @classmethod
    def guess_kind(cls, data):
        '''
        Guess the kind of the repository.
        '''
        if data.get('kind', None):
            pass
        else:
            if 'github.com' in data['url']:
                data['kind'] = 'github'
            elif 'bitbucket.org' in data['url']:
                data['kind'] = 'bitbucket'
            elif 'sourceforge.net' in data['url']:
                data['kind'] = 'sourceforge'
            elif 'gitlab.com' in data['url']:
                data['kind'] = 'gitlab'
            elif 'anaconda.org/bioconda' in data['url']:
                data['kind'] = 'bioconda'
            elif 'git.bioconductor.org' in data['url']:
                data['kind'] = 'bioconductor'
            else:
                data['kind'] = None

        return data

