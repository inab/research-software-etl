import re 

def find_github_repo(link):
    regex = re.compile(r'(http(s)?:\/\/)?(www\.)?github\.com\/[A-Za-z0-9_-]+\/[A-Za-z0-9_-]+')
    x = re.search(regex, link)
    if x:
        return x.group(0)
    else:
        return None

def find_bioconductor_link(link):
    regex = re.compile(r'(http(s)?:\/\/)?(www\.)?bioconductor\.org\/packages\/[A-Za-z0-9_-]+\/bioc\/html\/[A-Za-z0-9_-]+')
    x = re.search(regex, link)
    if x:
        return x.group(0) + '.html'
    else:
        return None

def find_bitbucket_repo(link):
    '''
    Find Bitbuket repository in URL string
    '''
    regex = re.compile(r'(http(s)?:\/\/)?(www\.)?bitbucket\.org\/[A-Za-z0-9_-]+\/[A-Za-z0-9_-]+')
    x = re.search(regex, link)
    if x:
        return x.group(0)
    else:
        return None

def find_galaxy_instance(link):
    '''
    Find Galaxy instance in URL string
    '''
    regex = re.compile(r'(http(s)?:\/\/)?(www\.)?usegalaxy\.eu')
    x = re.search(regex, link)
    if x:
        return x.group(0)
    else:
        return None

def find_galaxytoolshed_link(link):
    '''
    Find Galaxy toolshed in URL string
    '''
    regex = re.compile(r'(http(s)?:\/\/)?(www\.)?toolshed\.galaxyproject\.org')
    x = re.search(regex, link)
    if x:
        return x.group(0)
    else:
        return None



def prepare_sources_labels(sources, name, links):
    '''
    {
        "biotools" : URL,
        "bioconda" : URL,
        "biocontainers" : URL,
        "galaxy" : URL,
        "toolshed" : URL,
        "bioconductor" : URL,
        "sourceforge" : URL,
        "github" : URL,
        "bitbucket" : URL,
    }
    '''
    sources_labels = {}
    remain_sources = sources.copy()

    if 'opeb_metrics' in remain_sources:
        remain_sources.remove('opeb_metrics')

    if 'biotools' in sources:
        sources_labels['biotools'] = f'https://bio.tools/{name}'
        remain_sources.remove('biotools')

    if 'bioconda' in sources or 'bioconda_recipes' in sources:
        sources_labels['bioconda'] = f'https://anaconda.org/bioconda/{name}'
        if 'bioconda_recipes' in sources:
            remain_sources.remove('bioconda_recipes')
        if 'bioconda' in sources:
            remain_sources.remove('bioconda')

    if 'bioconductor' in sources:
        sources_labels['bioconductor'] = f'https://bioconductor.org/packages/release/bioc/html/{name}.html'
        remain_sources.remove('bioconductor')
    
    if 'sourceforge' in sources:
        sources_labels['sourceforge'] = f'https://sourceforge.net/projects/{name}'
        remain_sources.remove('sourceforge')
    
    if 'toolshed' in sources:
        sources_labels['toolshed'] = f'https://toolshed.g2.bx.psu.edu/repository'
        remain_sources.remove('toolshed')

    if 'galaxy_metadata' in remain_sources:
        sources_labels['toolshed'] = f'https://toolshed.g2.bx.psu.edu/repository'
        remain_sources.append('galaxy')
        remain_sources.remove('galaxy_metadata')
    
    if 'galaxy' in sources:
        sources_labels['galaxy'] = 'https://usegalaxy.eu/'
        remain_sources.remove('galaxy')


    for link in link:
        foundLink = False
        while not foundLink:
            # bioconda
            # some tools have bioconductor in name in some sources like bioconda
            if f'bioconductor-{name}' in link:
                sources_labels['bioconda'] = f'https://anaconda.org/bioconda/bioconductor-{name}'

            # github
            github_repo = find_github_repo(link)
            if github_repo:
                sources_labels['github'] = github_repo
                foundLink = True
                if 'github' in remain_sources:
                    remain_sources.remove('github')
            
            # bioconductor
            bioconductor_link = find_bioconductor_link(link)
            if bioconductor_link:
                sources_labels['bioconductor'] = bioconductor_link
                foundLink = True
                if 'bioconductor' in remain_sources:
                    remain_sources.remove('bioconductor')
            
            # bitbucket 
            bitbucket_repo = find_bitbucket_repo(link)
            if bitbucket_repo:
                sources_labels['bitbucket'] = bitbucket_repo
                foundLink = True
                if 'bitbucket' in remain_sources:
                    remain_sources.remove('bitbucket')

            # galaxy
            galaxy_instance = find_galaxy_instance(link)
            if galaxy_instance:
                sources_labels['galaxy'] = galaxy_instance
                foundLink = True
                if 'galaxy' in remain_sources:
                    remain_sources.remove('galaxy')

            # toolshed
            galaxytoolshed_link = find_galaxytoolshed_link(link)
            if galaxytoolshed_link:
                sources_labels['toolshed'] = galaxytoolshed_link
                foundLink = True
                if 'toolshed' in remain_sources:
                    remain_sources.remove('toolshed')

            foundLink = True

    for source in remain_sources:
        sources_labels[source] = ''

    return sources_labels
