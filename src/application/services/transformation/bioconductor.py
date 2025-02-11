from src.application.services.transformation.metadata_standardizers import MetadataStandardizer
from src.domain.models.software_instance.main import instance
from src.shared.utils import validate_and_filter

from pydantic import TypeAdapter, HttpUrl, EmailStr, ValidationError, BaseModel
from typing import Dict, Any, Optional, List
import re

# --------------------------------------------
# Bioconductor Tools Transformer
# --------------------------------------------

class User(BaseModel):
    email: EmailStr

class bioconductorStandardizer(MetadataStandardizer): 

    def __init__(self, source = 'bioconductor'):
        MetadataStandardizer.__init__(self, source)

    @staticmethod
    def description(tool: Dict[str, Any]):
        '''
        Returns the description of the tool.
        '''
        #logging.info('-- Getting the description of the tool --')

        if tool.get('Description'):
            return [tool.get('Description')]
        else:
            return []
            
    @staticmethod
    def clean_webpage(webpage: str) -> Optional[str]:
        if not webpage:  # Handle empty strings or None
            return None
        
        # Strip unwanted leading characters
        if webpage[0] in ['"', "'", '<']:
            webpage = webpage[1:]
        
        # Strip unwanted trailing characters
        if webpage and webpage[-1] in ['"', "'", '>']:
            webpage = webpage[:-1]

        # Correct malformed protocols
        if webpage.startswith('http//'):
            webpage = webpage.replace('http//', 'http://', 1)

        if webpage.startswith('https//'):
            webpage = webpage.replace('https//', 'https://', 1)
        
        # Add default protocol for URLs starting with "www."
        if webpage.startswith('www.'):
            webpage = 'https://' + webpage

        # Verify if the URL resolves
        if not webpage.startswith('http://') or not webpage.startswith('https://'):
            webpage = 'https://' + webpage
            return webpage
 
        else:
            return None

    @staticmethod
    def get_bioconductor_package_url(source_url: Optional[str]) -> List[str]:
        '''
        Returns the Bioconductor package URL if available.
        '''
        if source_url:
            source_url = source_url.replace(
                'https://git.bioconductor.org/packages/',
                'https://bioconductor.org/packages/'
            )
            return [source_url]
        else:
            return []

    @staticmethod
    def webpage(tool: Dict[str, Any], source_url: str) -> List[str]:
        '''
        Returns the webpage of the tool.
        '''
        # If the tool provides a URL
        tool_url = tool.get('URL')
        if tool_url:
            # Handle multiple URLs separated by ', '
            if ', ' in tool_url:
                urls = tool_url.split(', ')
                urls = [bioconductorStandardizer.clean_webpage(url) for url in urls]
                urls = [url for url in urls if url]  # Filter out None values
                return urls

            # Handle special case for 'TBA'
            if tool_url == 'TBA':
                return []

            # Handle a single URL
            webpage = bioconductorStandardizer.clean_webpage(tool_url)
            if webpage:
                return [webpage]
            else:
                return bioconductorStandardizer.get_bioconductor_package_url(source_url)

        # If no URL is provided, try the Bioconductor package URL
        return bioconductorStandardizer.get_bioconductor_package_url(source_url)

    @staticmethod
    def dependencies(tool: Dict[str, Any]):
        '''
        Returns the dependencies of the package
        '''
        #logging.info('-- Getting the dependencies of the tool --')

        dependencies = []
        if tool.get('Depends'):
            for package in tool.get('Depends'):
                dependencies.append(package.strip())
        
        if tool.get('Imports'):
            for package in tool.get('Imports'):
                dependencies.append(package.strip())

        return dependencies
    
    @staticmethod
    def license(tool: Dict[str, Any]):
        '''
        Returns the license of the package
        '''
        #logging.info('-- Getting the license of the tool --')

        licenses = []
        if tool.get('License'):
            ta = TypeAdapter(HttpUrl)
            for license in tool.get('License'):
                try:
                    if ta.validate_python(license):
                        licenses.append({
                            'url': license
                            })
                except:
                    licenses.append({
                        'name': license
                        })
        return licenses

    @staticmethod
    def clean_email(email):
        '''
        Cleans the email of the author
        '''
        if email:
            if email[-1] in [';','>']:
                email = email[:-1]
            
            if email in ['-','DECEASED']:
                email = None

            # validate email and drop if invalid
            try:
                user = User(email=email)
            except ValidationError as e:
                return None
            else:
                return email          

    @staticmethod
    def authors(tool: Dict[str, Any]):
        #logging.info('-- Getting the authors of the tool --')

        all_results = []
        maintainers = set()
        for maintainer in tool.get('Maintainer', []):
            if maintainer.get('name') == '':
                continue
                
            if maintainer.get('email'):
                maintainer['email'] = bioconductorStandardizer.clean_email(maintainer['email'])

            all_results.append(maintainer)
            [maintainers.add(item.get('name')) for item in all_results]

        # go through maintainers and see if the maintainer is among authors
        # logging.info('----- Authors@R -----')
        if tool.get('Authors@R (parsed)'):
            for author in tool.get('Authors@R (parsed)', []):
                if author['name'] in maintainers:
                    continue
                else:
                    if author['name'] == '':
                        continue

                    if author.get('email'):
                        author['email'] = bioconductorStandardizer.clean_email(author['email'])

                    all_results.append(author)
            
        return all_results
    
    @staticmethod
    def find_github_repo(string):
        # Regex pattern to match a GitHub repository URL and capture the username/repo part
        github_repo_pattern = r'https://github\.com/([A-Za-z0-9][A-Za-z0-9_-]*/[A-Za-z0-9_.-]+)'

        # Search for GitHub repo URL using the regex pattern
        match = re.search(github_repo_pattern, string)

        # Return the captured username/repo part if a match is found, else return None
        if match:
            return f"https://github.com/{match.group(1)}"
        else:
            return None
        
    @staticmethod
    def repositories(tool: Dict[str, Any], source_url: str):
        '''
        Returns the repositories of the package
        '''
        #logging.info('-- Getting the repositories of the tool --')
        repositories = []
        if source_url:
            repositories.append({
                'url': source_url
            })
        if tool.get('BugReports'):
            repo = bioconductorStandardizer.find_github_repo(tool.get('BugReports'))
            if repo:
                repositories.append({
                    'url': repo,
                    'kind': 'github'
                })
        
        return repositories

    @staticmethod
    def documentation(tool: Dict[str, Any]):
        '''
        NOT USED FOR NOW - not present in the raw metadata ...
        Returns the documentation of the tool.
        '''
        documentation = []
        if tool.get('documentation'):
            for key in tool['documentation'].keys():
                if tool['documentation'][key]:
                    documentation.append({
                        'type': key,
                        'url': tool['documentation'][key]            
                    })

        return(documentation)
    

    @classmethod    
    def transform_one(cls, tool, standardized_tools):
        '''
        Transforms a single tool into an instance.
        '''
        source_url = tool.get('@source_url')
        tool = tool.get('data')

        name = name = cls.clean_name(tool.get('Package')).lower()
        type_ = 'lib'
        version = [tool.get('Version')]
        label = cls.clean_name(tool.get('Package'))
        description = cls.description(tool)
        webpage = cls.webpage(tool, source_url)
        source = ['bioconductor']
        operating_system = ['Linux', 'macOS', 'Windows']
        license = cls.license(tool)
        dependencies = cls.dependencies(tool)
        authors = cls.authors(tool)
        repository = cls.repositories(tool, source_url)

        new_instance_dict = {
            "name" : name,
            "type" : type_,
            "version" : version,
            "source" : source,
            "label" : label,
            "description" : description,
            "license" : license,
            "operating_system" : operating_system,
            "repository" : repository,
            "webpage" : webpage,
            "dependencies" : dependencies,
            "authors" : authors,
        }

        # We keep only the fields that pass the validation
        new_instance = validate_and_filter(instance, **new_instance_dict)
        
        standardized_tools.append(new_instance)

        return standardized_tools
