from src.application.services.transformation.metadata_standardizers import MetadataStandardizer
from src.domain.models.software_instance.main import instance

from pydantic import TypeAdapter, HttpUrl, EmailStr, ValidationError, BaseModel
from typing import Dict, Any, Optional, List
import logging
import re
import requests

# --------------------------------------------
# Bioconductor Tools Transformer
# --------------------------------------------

class User(BaseModel):
    email: EmailStr

class bioconductorStandardizer(MetadataStandardizer): 

    def __init__(self, source = 'bioconductor'):
        MetadataStandardizer.__init__(self, source)

    @classmethod
    def description(self, tool: Dict[str, Any]):
        '''
        Returns the description of the tool.
        '''
        #logging.info('-- Getting the description of the tool --')

        if tool.get('Description'):
            return [tool.get('Description')]
        
        else:
            return []
        
    @staticmethod
    def check_url_resolves(url: str, timeout: int = 5) -> bool:
        '''
        Checks if a URL resolves. Returns True if the URL resolves, else False.
        TODO: move to utils or similar so other transformers can use it.
        '''
        def try_url(protocol: str, base_url: str) -> bool:
            try:
                full_url = f"{protocol}://{base_url}" if not base_url.startswith((f"{protocol}://")) else base_url
                response = requests.head(full_url, allow_redirects=True, timeout=timeout)
                return response.status_code < 400
            except requests.RequestException:
                return False

        # Check if protocol is already present; if not, assume https
        if "://" not in url:
            url = f"https://{url}"

        # Attempt with the original protocol (https by default)
        if try_url("https", url):
            return True

        # Fallback to http if https fails
        return try_url("http", url)
            
    def clean_webpage(self, webpage: str) -> Optional[str]:
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
            if self.check_url_resolves(webpage):
                return webpage
            else:
                return None
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

    @classmethod
    def webpage(cls, tool: Dict[str, Any], source_url: str) -> List[str]:
        '''
        Returns the webpage of the tool.
        '''
        # If the tool provides a URL
        tool_url = tool.get('URL')
        if tool_url:
            # Handle multiple URLs separated by ', '
            if ', ' in tool_url:
                urls = tool_url.split(', ')
                urls = [cls().clean_webpage(url) for url in urls]
                urls = [url for url in urls if url]  # Filter out None values
                return urls

            # Handle special case for 'TBA'
            if tool_url == 'TBA':
                return []

            # Handle a single URL
            webpage = cls().clean_webpage(tool_url)
            if webpage:
                return [webpage]
            else:
                return cls.get_bioconductor_package_url(source_url)

        # If no URL is provided, try the Bioconductor package URL
        return cls.get_bioconductor_package_url(source_url)

    @classmethod
    def dependencies(self, tool: Dict[str, Any]):
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
    
    @classmethod
    def license(self, tool: Dict[str, Any]):
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
                logging.info(f"Invalid email: {email}. Error: {e}")
                return None
            else:
                return email          

    @classmethod
    def authors(self, tool: Dict[str, Any]):
        #logging.info('-- Getting the authors of the tool --')

        all_results = []
        maintainers = set()
        for maintainer in tool.get('Maintainer', []):
            if maintainer.get('name') == '':
                continue
                
            if maintainer.get('email'):
                maintainer['email'] = self.clean_email(maintainer['email'])

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
                        author['email'] = self.clean_email(author['email'])

                    all_results.append(author)
            
        return all_results
    
    @classmethod
    def find_github_repo(self, string):
        # Regex pattern to match a GitHub repository URL and capture the username/repo part
        github_repo_pattern = r'https://github\.com/([A-Za-z0-9][A-Za-z0-9_-]*/[A-Za-z0-9_.-]+)'

        # Search for GitHub repo URL using the regex pattern
        match = re.search(github_repo_pattern, string)

        # Return the captured username/repo part if a match is found, else return None
        if match:
            return f"https://github.com/{match.group(1)}"
        else:
            return None
        
    @classmethod
    def repositories(self, tool: Dict[str, Any], source_url: str):
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
            repo = self.find_github_repo(tool.get('BugReports'))
            if repo:
                repositories.append({
                    'url': repo,
                    'kind': 'github'
                })
        
        return repositories

    def documentation(self, tool: Dict[str, Any]):
        '''
        NOT USED FOR NOW
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
    
    
    def transform_one(self, tool, standardized_tools):
        '''
        Transforms a single tool into an instance.
        '''
        source_url = tool.get('@source_url')
        tool = tool.get('data')

        name = name = self.clean_name(tool.get('Package')).lower()
        type_ = 'lib'
        version = [tool.get('Version')]
        label = self.clean_name(tool.get('Package'))
        description = self.description(tool)
        webpage = self.webpage(tool, source_url)
        source = ['bioconductor']
        operating_system = ['Linux', 'macOS', 'Windows']
        license = self.license(tool)
        dependencies = self.dependencies(tool)
        authors = self.authors(tool)
        repository = self.repositories(tool, source_url)

        #citation = self.citation(tool)

        new_instance = instance(
            name = name,
            type = type_,
            version = version,
            source = source,
            label = label,
            description = description,
            license = license,
            operating_system = operating_system,
            repository = repository,
            webpage = webpage,
            dependencies = dependencies,
            authors = authors,
            )
        
        standardized_tools.append(new_instance)

        return standardized_tools
