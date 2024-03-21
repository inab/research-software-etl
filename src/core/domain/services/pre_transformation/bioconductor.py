from FAIRsoft.transformation.utils import toolGenerator
from FAIRsoft.classes.main import setOfInstances
from FAIRsoft.classes.main import instance
from FAIRsoft.classes.EDAM_forFE import EDAMDict

from pydantic import TypeAdapter, HttpUrl, BaseModel, model_validator
from typing import List, Dict, Any
import logging
import re

# --------------------------------------------
# Bioconductor Tools Transformer
# --------------------------------------------

class bioconductorToolsGenerator(toolGenerator): 

    def __init__(self, tools, source = 'bioconductor'):
        toolGenerator.__init__(self, tools, source)

        self.instSet = setOfInstances('bioconductor')

        self.transform()

    @classmethod
    def description(self, tool: Dict[str, Any]):
        '''
        Returns the description of the tool.
        '''
        if tool.get('description'):
            return [tool.get('description')]
        
        else:
            return []
    
    @classmethod
    def webpage(self, tool: Dict[str, Any]):
        '''
        Returns the webpage of the tool.
        '''
        if tool.get('URL'):
            return [tool.get('URL')]
        
        else:
            return [tool.get('@source_url')]
        
    @classmethod
    def citation(self, tool: Dict[str, Any]):
        '''
        Returns the citation of the tool.
        '''
        if tool.get('publiction'):
            return [tool.get('publiction')]
        
        else:
            return []
    
    @classmethod
    def publication(self, tool: Dict[str, Any]):
        '''
        Returns the publication of the tool.
        '''
        if tool['publication'].get('url'):
            if tool['publication']['citation'].get('type') == 'article-journal':
                journal = None
                for a in tool['publication']['citation']['container-title']:
                    if 'ISSN' not in a:
                        journal = a
                
                fields = {}
                for field in ['date', 'title']:
                    if tool['publication']['citation'].get(field):
                        fields[field] = tool['publication']['citation'][field][0]
                    else:
                        fields[field] = None
                
                if tool['publication'].get('url'):
                    url = tool['publication']['url'][0]
                else:
                    url = None

                if tool['publication']['citation'].get('doi'):
                    doi = tool['publication']['citation']['doi'][0]
                
                return  [{
                    'title': fields['title'],
                    'year': fields['date'],
                    'url': url,
                    'journal': journal,
                    'doi': doi
                    }]
        
        return []

    @classmethod
    def download(self, tool: Dict[str, Any]):
        '''
        Returns the download links of the tool.
        '''
        download = set()
        for a in ["Windows Binary", "Source Package", "Mac OS X 10 10.11 (El Capitan)", "macOS Binary (x86_64)", "macOS Binary (arm64)"]:
            if a in tool.keys() and tool[a]:
                download.add(tool.get('Package Short Url') + tool[a])
        
        return list(download)
    
    @classmethod
    def source_code(self, tool: Dict[str, Any]):
        '''
        Returns the source code links of the tool.
        '''
        source_code = []
        if tool.get('Source Package'):
            source_code.append(tool.get('Package Short Url') + tool.get('Source Package'))
        
        return source_code
    
    @classmethod
    def dependencies(self, tool: Dict[str, Any]):
        '''
        Returns the dependencies of the package
        '''
        dependencies = []
        if tool.get('Depends'):
            return tool.get('Depends')
        
        if tool.get('Imports'):
            for package in tool.get('Imports').split(','):
                dependencies.append(package.strip())

        return dependencies
    
    @classmethod
    def license(self, tool: Dict[str, Any]):
        '''
        Returns the license of the package
        '''
        license = []
        if tool.get('License'):
            ta = TypeAdapter(HttpUrl)
            try:
                if ta.validate_python(tool.get('License')):
                    license.append({
                        'url': tool.get('License')
                        })
            except:
                license.append({
                    'name': tool.get('License')
                    })
                
            
        return license
    

    @classmethod
    def find_names(self, string):
        name_pattern = r'\b[A-Z][a-z]*\s[A-Z][a-z]*\b|\b[A-Z][a-z]*\s[A-Z]\.\s[A-Z][a-z]*\b'
        return re.findall(name_pattern, string)

    @classmethod
    def process_only_names(self, string):
        names= self.find_names(string)
        results = []
        for name in names:
            results.append({
            'name': name,
            'type': 'Person'
            })
        return results

    @classmethod
    def find_names_from(self, string):
        pattern = r'(?<=\bfrom\s)([A-Z][a-z]*\s[A-Z][a-z]*\b|[A-Z][a-z]*\s[A-Z]\.\s[A-Z][a-z]*\b|[A-Z][a-z]*\s[A-Z][a-z]*(-[A-Z][a-z]*)?\b)'
        matches = re.findall(pattern, string)
        new_matches = []
        for m in matches:
            new_matches.append(m[0])
        
        return new_matches

    @classmethod
    def find_name_email_pairs(self, matches):
        results = []
        for match in matches:
            name = match[0].strip()
            name = self.find_names(name)[0]
            email = match[1].replace(' at ', '@').lower()
            results.append({
                'name': name,
                'email': email,
                'type': 'Person'
                })
        return results

    @classmethod
    def find_name_email(self, string, maintainer = False):
        results = []
        # Pattern to match name and email pairs
        pair_pattern = r"([\w\s.]+?) *<([\w\.]+ at \w+\.\w+(\.\w+)?)>"

        # Find all matches of the pattern
        matches = re.findall(pair_pattern, string)

        # If no matches, find only names
        if len(matches)>0:
            # name-email pairs
            pairs = self.find_name_email_pairs(matches)
            for author in pairs:
                author['maintainer'] = maintainer
                results.append(author)
            
            # only name stracted
            names = self.find_names_from(string)
            names_in_pairs = [item['name'] for item in pairs]
            for name in names:
                if name in names_in_pairs:
                    continue
                else:
                    results.append({
                        'name' : name,
                        'type': 'Person',
                        'maintainer': maintainer
                    })
        # No emails in this string
        else:
            new_authors = self.process_only_names(string)
            for author in new_authors:
                author['maintainer'] = maintainer
            results.extend(new_authors)
        

        return results
    

    @classmethod
    def authors(self, tool: Dict[str, Any]):

        all_results = []
        maintainers = set()
        for sentence in tool.get('mantainers'):
            all_results.extend(self.find_name_email(sentence, True))
            [maintainers.add(item['name']) for item in all_results]

        # go through maintainers and see if the maintainer is among authors
        for sentence in tool.get('authors'):
            new_authors = self.find_name_email(sentence)
            for author in new_authors:
                if author['name'] in maintainers:
                    continue
                else:
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
    def repositories(self, tool: Dict[str, Any], webpages):
        '''
        Returns the repositories of the package
        '''
        repositories = []
        if tool.get('Source Repository'):
            url = tool.get('Source Repository').split('gitclone')[1]
            repositories.append({
                'url': url
            })
        if tool.get('BugReports'):
            repo = self.find_github_repo(tool.get('BugReports'))
            if repo:
                repositories.append({
                    'url': repo,
                    'kind': 'github'
                })
        
        for webpage in webpages:
            repo = self.find_github_repo(webpage)
            if repo:
                repositories.append({
                    'url': repo,
                    'kind': 'github'
                })
        
        return repositories

    def documentation(self, tool: Dict[str, Any]):
        '''
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
    
    def transform_single_tool(self, tool):
        '''
        Transforms a single tool into an instance.
        '''
        name = name = self.clean_name(tool.get('name')).lower()
        type_ = 'lib'
        version = [tool.get('Version')]
        label = self.clean_name(tool.get('name'))
        description = self.description(tool)
        webpage = self.webpage(tool)
        publication = self.publication(tool)
        download = self.download(tool)
        source = ['bioconductor']
        source_code = self.source_code(tool)
        operating_system = ['Linux', 'macOS', 'Windows']
        license = self.license(tool)
        dependencies = self.dependencies(tool)
        authors = self.authors(tool)
        repository = self.repositories(tool, webpage)
        documentation = self.documentation(tool)
        citation = self.citation(tool)

        new_instance = instance(
            name = name,
            type = type_,
            version = version,
            source = source,
            download = download,
            label = label,
            description = description,
            publication = publication,
            source_code = source_code,
            license = license,
            documentation = documentation,
            operating_system = operating_system,
            repository = repository,
            webpage = webpage,
            dependencies = dependencies,
            authors = authors,
            citation = citation
            )
            
        
        self.instSet.instances.append(new_instance)


    def transform(self):
        '''
        Performs the transformation of the raw metadata of tools into instances (homogenized and standardized).
        '''
        
        for tool in self.tools:
            
            try:
                self.transform_single_tool(tool)
            except Exception as e:
                logging.error(f"Error transforming tool {tool['@id']}: {e}")
                continue
            
            