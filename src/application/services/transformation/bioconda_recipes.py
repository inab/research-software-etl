from src.application.services.transformation.metadata_standardizers import MetadataStandardizer
from src.domain.models.software_instance.main import instance

import logging
import re
from pydantic import HttpUrl, TypeAdapter
from typing import List, Dict

# ------------------------------------------
# Bioconda Recipes Transformer
# ------------------------------------------

class biocondaRecipesStandardizer(MetadataStandardizer):
    def __init__(self, source = 'bioconda_recipes'):
        MetadataStandardizer.__init__(self, source)

    @classmethod
    def name(self, tool):
        '''
        Build the name of the tool.
        - tool: dictionary with the tool data
        '''
        name = self.clean_name(tool.get('name')).lower()
        return name

    @classmethod
    def type(self, tool):
        '''
        Builds the type of the tool. If there is no type in the document, it returns cmd.
        - tool: dictionary with the tool data
        '''
        if tool.get('type'):
            return tool.get('type')
        else:
            return ['cmd']

    @classmethod
    def version(self, tool):
        '''
        Builds the version of the tool. The version is extracted from the @id field.
        - tool: dictionary with the tool data
        '''
        if tool.get('package'):
            if tool['package'].get('version'):
                return [tool['package']['version']]
        else:
            return None
        
    @classmethod
    def description(self, tool: Dict) -> List[str]:
        '''
        Builds the description of the tool.
        - tool: dictionary with the tool data
        '''
        if tool.get('about'):
            if tool['about'].get('description'):
                description = tool['about']['description']
                return [description]
            
            elif tool['about'].get('summary'):
                description = tool['about']['summary']
                return [description]
        
        return []
            
    @classmethod
    def webpage(self, tool: Dict) -> List[HttpUrl]:
        '''
        Builds the webpage of the tool.
        - tool: dictionary with the tool data
        '''
        try:
            webpage = tool['about']['home']
            return [webpage]
        except:
            return []
        
    @classmethod
    def source_code(self, tool: Dict) -> List[HttpUrl]:
        '''
        Builds the source code of the tool.
        - tool: dictionary with the tool data
        '''
        source_code = []
        try:
            source_url = tool['source'].get('url')

            # if source_url is a list of strings, we take all as source_url
            if isinstance(source_url, list):
                source_code = source_url
            elif isinstance(source_url, str):
                source_code = [source_url]

            logging.info(f"Source code: {source_code}")
        except:
            pass

        return source_code
    

    @classmethod
    def documentation(self, tool: Dict) -> List[Dict]:
        '''
        Builds the documentation of the tool.
        - tool: dictionary with the tool data
        '''
        documentation = []
        # Installation instructions in Bioconda page
        if tool.get('name'):
            # make sure the page exists
            if self.page_exists(f"https://bioconda.github.io/recipes/{tool['name']}/README.html"):
                documentation.append({
                    'type': 'installation_instructions',
                    'url': f"https://bioconda.github.io/recipes/{tool['name']}/README.html"
                })
                documentation.append({
                    'type': 'general',
                    'url': f"https://bioconda.github.io/recipes/{tool['name']}/README.html"
                })

        # Documentation in the about field
        if tool.get('about'):
            ta=TypeAdapter(HttpUrl)
            if tool['about'].get('docs'):
                # make sure value is a url
                if ta.validate_strings(tool['about']['docs']):
                    documentation.append({
                        'type': 'general',
                        'url': tool['about']['docs']
                    })
            
            elif tool['about'].get('doc_url'):
                # make sure value is a url
                if ta.validate_strings(tool['about']['doc_url']):
                    documentation.append({
                        'type': 'general',
                        'url': tool['about']['home']
                    })

        return documentation
    
    @classmethod
    def is_github_repo(self, url):
        '''
        Checks if the url is a github repository.
        - url: url to check
        '''
        if 'github.com' in url:
            end =  url.split('github.com/')[1]
            owner = end.split('/')[0]
            repo = end.split('/')[1]

            clean_repo = f"https://github.com/{owner}/{repo}"

            if self.page_exists(clean_repo):
                return clean_repo
            
        else:
            return None
        
    @classmethod
    def is_gitlab_repo(self, url):
        '''
        Checks if the url is a gitlab repository.
        - url: url to check
        '''
        if 'gitlab.com' in url:
            end =  url.split('gitlab.com/')[1]
            owner = end.split('/')[0]
            repo = end.split('/')[1]
         
            clean_repo = f"https://gitlab.com/{owner}/{repo}"

            if self.page_exists(clean_repo):
                return clean_repo
            
        else:
            return None
        
    @classmethod
    def is_bitbucket_repo(self, url):
        '''
        Checks if the url is a bitbucket repository.
        - url: url to check
        '''
        if 'bitbucket.org' in url:
            end =  url.split('bitbucket.org/')[1]
            owner = end.split('/')[0]
            repo = end.split('/')[1]
         
            clean_repo = f"https://bitbucket.org/{owner}/{repo}"

            if self.page_exists(clean_repo):
                return clean_repo
            
        else:
            return None
    
    @classmethod
    def is_repository(self, url):
        '''
        Checks if the url is a repository.
        - url: url to check
        '''
        if self.is_github_repo(url):
            return self.is_github_repo(url)
        elif self.is_gitlab_repo(url):
            return self.is_gitlab_repo(url)
        elif self.is_bitbucket_repo(url):
            return self.is_bitbucket_repo(url)
        else:
            return []
        

    @classmethod
    def repository(self, tool: Dict) -> List[HttpUrl]:
        '''
        Builds the repository of the tool.
        - tool: dictionary with the tool data
        '''
        repository = []
        # It can be in about/home
        if tool.get('about'):
            if tool['about'].get('home'):
                repository = self.is_repository(tool['about']['home'])
                if repository:
                    return [{
                        'url': repository
                    }]
        
        # It can be in about/dev_url
        if tool.get('about'):
            if tool['about'].get('dev_url'):
                repository = self.is_repository(tool['about']['dev_url'])
                if repository:
                    return [{
                        'url': repository
                    }]
        
        # It can be in source/url
        if tool.get('source'):
            if tool['source'].get('url'):
                repository = self.is_repository(tool['source']['url'])
                if repository:
                    return [{
                        'url': repository
                    }]

        return repository


    @classmethod
    def license(self, tool: Dict) -> List[Dict]:
        '''
        Builds the license of the tool.
        - tool: dictionary with the tool data
        '''
        license = []
        if tool.get('about'):
            if tool['about'].get('license'):
                license = tool['about']['license']
                license = {
                    'name': license,
                    'url': None
                }
                return [license]
    
    @classmethod
    def publications(self, tool: Dict) -> List[Dict]:
        '''
        Builds the publications of the tool.
        - tool: dictionary with the tool data
        Publication DOI identifiers can be in extra/identifiers or extra/doi.
        '''
        new_pubids = set()
        if tool.get('extra'):
            if tool['extra'].get('identifiers'):
                for ident in tool['extra'].get('identifiers'):
                    reg1 = 'https:\/\/doi.org\/(10.([\w.]+?)\/([\w.]+)([\w.\/]+)?)'
                    reg2 = 'doi:(10.([\w.]+?)\/([\w.]+)([\w.\/]+)?)'
                    m1 = re.match(reg1, ident)
                    m2 = re.match(reg2, ident)
                    if m1:
                        new_pubids.add(m1.group(1))
                    if m2:
                        new_pubids.add(m2.group(1))

            if tool['extra'].get('doi'):
                for doi in tool['extra'].get('doi'):
                    new_pubids.add(doi)
        
        publications = []
        for pubid in new_pubids:
            publications.append({
                'doi': pubid
            })
    
        return publications
    
    @classmethod
    def dependencies(self, tool: Dict) -> List[Dict]:
        '''
        Builds the dependencies of the tool.
        - tool: dictionary with the tool data
        Only run dependencies are considered. Host could be added in the future.
        '''
        dependencies = []
        if tool.get('requirements'):
            if tool['requirements'].get('run'):
                for dep in tool['requirements']['run']:
                    dependencies.append(dep)

        return dependencies
    
    @classmethod
    def extract_github_user(self, name):
        '''
        '''
        if len(name.split(' ')) == 1:
            # if github page exists
            if self.page_exists(f"https://github.com/{name}"):
            
                return({
                    'type': 'Person',
                    'url': f"https://github.com/{name}",
                })
        
        return {}
    

    @classmethod
    def convert_names_to_list(self, names_str):
        # Replace ' and ' with ', ' to standardize separators
        standardized_str = names_str.replace(' and ', ', ')
        # Split the string by ', ' to create a list
        names_list = standardized_str.split(', ')
        return names_list

    @classmethod
    def authors(self, tool: Dict) -> List[Dict]:
        '''
        Builds the authors of the tool.
        - tool: dictionary with the tool data
        Authors can be in about/maintainer and about/author and are normally people.
        '''
        authors = []
        maintainers = set()
        
        if tool.get('about'):
            if tool['about'].get('maintainers'):
                raw_authors = tool['about']['maintainers']
                if isinstance(raw_authors, str):
                    raw_authors = self.convert_names_to_list(raw_authors)

                for maintainer in raw_authors:
                    maintainers.add(maintainer)
                    # check if this seems a github user
                    if self.extract_github_user(maintainer):
                        user = self.extract_github_user(maintainer)
                        user['maintainer'] = True
                        authors.append(user)
                    else:
                        authors.append({
                            'name': maintainer,
                            'type': 'Person',
                            'maintainer': True
                        })
        
            if tool['about'].get('authors'):
                raw_authors = tool['about']['authors']

                if isinstance(raw_authors, str):
                    raw_authors = self.convert_names_to_list(raw_authors)
                    

                for author in raw_authors:
                    if author in maintainers:
                        continue
                    # check if this seems a github user
                    if self.extract_github_user(author):
                        user = self.extract_github_user(author)
                        user['maintainer'] = False
                        authors.append(user)
                    else:
                        authors.append({
                            'name': author,
                            'type': 'Person',
                            'maintainer': False
                        })

        return authors
    

    def transform_one(self, tool, standardized_tools):
        '''
        Transforms a single tool into an instance.
        '''
        tool = tool['data']

        name = self.name(tool)
        types_ = self.type(tool)
        version = self.version(tool)
        source = ['bioconda_recipes']
        label = self.clean_name(tool.get('name'))
        description = self.description(tool)
        webpage = self.webpage(tool)
        source_code = self.source_code(tool)
        documentation = self.documentation(tool)
        repository = self.repository(tool)
        operating_system = ['Linux', 'macOS', 'Windows']
        license = self.license(tool)
        publication = self.publications(tool)
        dependencies = self.dependencies(tool)
        authors = self.authors(tool)
        test = False

        for type_ in types_:

            new_instance = instance(
                name = name,
                type = type_,
                version = version,
                source = source,
                label = label,
                description = description,
                source_code = source_code,
                download = source_code,
                publication = publication,
                test = test,
                license = license,
                documentation = documentation,
                operating_system = operating_system,
                repository = repository,
                webpage = webpage,
                dependencies = dependencies,
                authors = authors
                )
            
            standardized_tools.append(new_instance)
        
        return standardized_tools
