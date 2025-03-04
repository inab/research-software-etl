import logging
from pydantic import HttpUrl, ValidationError
from typing import List, Dict
from src.application.services.transformation.metadata_standardizers import MetadataStandardizer
from src.domain.models.software_instance.main import instance
from src.shared.utils import validate_and_filter, is_repository

logger = logging.getLogger("rs-etl-pipeline")

# ------------------------------------------
# Bioconda Recipes Transformer
# ------------------------------------------

class biocondaRecipesStandardizer(MetadataStandardizer):
    def __init__(self, source = 'bioconda_recipes'):
        MetadataStandardizer.__init__(self, source)

    @classmethod
    def name(cls, tool):
        '''
        Build the name of the tool.
        - tool: dictionary with the tool data
        '''
        name = cls.clean_name(tool.get('name')).lower()
        return name

    @staticmethod
    def type(tool):
        '''
        Builds the type of the tool. If there is no type in the document, it returns cmd.
        - tool: dictionary with the tool data
        '''
        if tool.get('@type'):
            return [tool.get('@type')]
        else:
            return ['cmd']

    @staticmethod
    def version(tool):
        '''
        Builds the version of the tool. The version is extracted from the @id field.
        - tool: dictionary with the tool data
        '''
        if tool.get('package'):
            if tool['package'].get('version'):
                return [tool['package']['version']]
        else:
            return None
        
    @staticmethod
    def description(tool: Dict) -> List[str]:
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
            
    @staticmethod
    def webpage(tool: Dict) -> List[HttpUrl]:
        '''
        Builds the webpage of the tool.
        - tool: dictionary with the tool data
        '''
        try:
            webpage = tool['about']['home']
            return [webpage]
        except:
            return []
        
    @staticmethod
    def source_code(tool: Dict) -> List[HttpUrl]:
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

            logger.info(f"Source code: {source_code}")
        except:
            pass

        return source_code
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        try:
            HttpUrl(url)
            return True
        except ValidationError:
            return False


    @staticmethod
    def documentation(tool: Dict) -> List[Dict]:
        '''
        Builds the documentation of the tool.
        - tool: dictionary with the tool data
        '''
        documentation = []
        # Installation instructions in Bioconda page
        if tool.get('name'):
            documentation.append({
                'type': 'installation_instructions',
                'url': f"https://bioconda.github.io/recipes/{tool['name']}/README.html"
            })

        # Documentation in the about field
        if tool.get('about'):
            if tool['about'].get('docs'):
                # make sure value is a url
                if biocondaRecipesStandardizer.is_valid_url(tool['about']['docs']):
                    documentation.append({
                        'type': 'general',
                        'url': tool['about']['docs']
                    })
            
            elif tool['about'].get('doc_url'):
                # make sure value is a url
                if biocondaRecipesStandardizer.is_valid_url(tool['about']['doc_url']):
                    documentation.append({
                        'type': 'general',
                        'url': tool['about']['home']
                    })

        return documentation
    
    from pydantic import HttpUrl, ValidationError

    

    @staticmethod
    def repository(tool: Dict) -> List[HttpUrl]:
        '''
        Builds the repository of the tool.
        - tool: dictionary with the tool data
        '''
        repository = []
        # It can be in about/home
        if tool.get('about'):
            if tool['about'].get('home'):
                repository = is_repository(tool['about']['home'])
                if repository:
                    return repository
        
        # It can be in about/dev_url
        if tool.get('about'):
            if tool['about'].get('dev_url'):
                repository = is_repository(tool['about']['dev_url'])
                if repository:
                    return repository
        
        # It can be in source/url
        if tool.get('source'):
            # if source is a dict 
            if isinstance(tool['source'], dict):
                if tool['source'].get('url'):
                    repository = is_repository(tool['source']['url'])
                    if repository:
                        return repository

            # if source is a list of dicts
            elif isinstance(tool['source'], list):
                for source in tool['source']:
                    if source.get('url'):
                        repository = is_repository(source['url'])
                        if repository:
                            return repository

        return repository


    @staticmethod
    def license(tool: Dict) -> List[Dict]:
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
    
    @staticmethod
    def dependencies(tool: Dict) -> List[Dict]:
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
    
    @staticmethod
    def extract_github_user(name):
        '''
        Heuristic from observation of the data.
        '''
        if len(name.split(' ')) == 1:

            return({
                'type': 'Person',
                'url': f"https://github.com/{name}",
            })
        
        return {}
    
    @staticmethod
    def convert_names_to_list(names_str):
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
                    raw_authors = biocondaRecipesStandardizer.convert_names_to_list(raw_authors)

                for maintainer in raw_authors:
                    maintainers.add(maintainer)
                    # check if this seems a github user
                    github_user = biocondaRecipesStandardizer.extract_github_user(maintainer)
                    if github_user:
                        user = github_user
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
                    github_user = biocondaRecipesStandardizer.extract_github_user(author)
                    if github_user:
                        user = github_user
                        user['maintainer'] = False
                        authors.append(user)
                    else:
                        authors.append({
                            'name': author,
                            'type': 'Person',
                            'maintainer': False
                        })

        return authors
    

    @classmethod
    def transform_one(cls, tool, standardized_tools):
        '''
        Transforms a single tool into an instance.
        '''
        tool = tool['data']

        name = cls.name(tool)
        types_ = cls.type(tool)
        version = cls.version(tool)
        source = ['bioconda_recipes']
        label = cls.clean_name(tool.get('name'))
        description = cls.description(tool)
        webpage = cls.webpage(tool)
        source_code = cls.source_code(tool)
        documentation = cls.documentation(tool)
        repository = cls.repository(tool)
        operating_system = ['Linux', 'macOS', 'Windows']
        license = cls.license(tool)
        # publication = self.publications(tool) TODO: to be moved out of here
        dependencies = cls.dependencies(tool)
        authors = cls.authors(tool)
        test = False

        for type_ in types_:

            new_instance_dict = {
                "name" : name,
                "type" : type_,
                "version" : version,
                "source" : source,
                "label" : label,
                "description" : description,
                "source_code" : source_code,
                "download" : source_code,
                "test" : test,
                "license" : license,
                "documentation" : documentation,
                "operating_system" : operating_system,
                "repository" : repository,
                "webpage" : webpage,
                "dependencies" : dependencies,
                "authors" : authors
            }
            
            # We keep only the fields that pass the validation
            new_instance = validate_and_filter(instance, **new_instance_dict)
            
            standardized_tools.append(new_instance)
        
        return standardized_tools
