'''
--------------------------------------------
                DEPRECATED
--------------------------------------------
New importer of repositories in the making.
'''
from core.domain.services.transformation.metadata_standardizers import toolGenerator
from src.core.domain.entities.software_instance.main import instance, setOfInstances


from typing import List, Dict, Any 
import logging
import re

# --------------------------------------------
# Repository Tools Transformer
# --------------------------------------------

class repositoryToolsGenerator(toolGenerator):

    def __init__(self, tools, source = 'repository'):
        toolGenerator.__init__(self, tools, source)

        self.instSet = setOfInstances('repository')

        self.transform()
    
    def types(self, tool: Dict[str, Any], name: str, type_: str):
        '''
        Returns the types of the tool.
        - tool: tool to be transformed
        '''
        types_ = [type_]
        # We get the types from the bioconda_types dictionary
        if self.bioconda_types.get(name):
            types_ = [self.bioconda_types[name]]
        
        # If there is no type in bioconda_types, we assume cmd
        if type_ == 'workflow' and 'galaxy' in tool['@id']:
            types_ = ['cmd']

        return(types_)
    
    @classmethod
    def version(self, tool: Dict[str, Any], version: str) -> List[str]:
        '''
        Returns the version of the tool.
        - tool: tool to be transformed
        '''
        print(version)
        if version == None:
            versions = []
        
        else: 
            versions = [version]


        if tool['repos'][0]['res'].get('tool_versions'):
            versions.extend(tool['repos'][0]['res']['tool_versions'])
        
    
        return(versions)
    
    @classmethod
    def download(self, tool: Dict[str, Any]) -> List[List[str]]:
        '''
        Returns the download information of the tool.
        - tool: tool to be transformed
        '''
        download = []
        if tool['repos'][0]['res'].get('binaries'):
            if tool['repos'][0]['res']['binaries'].get('binary_uri'):
                download.append(tool['repos'][0]['res']['binaries'].get('binary_uri'))

        for link in tool['repos'][0].get('links'):
            x = re.search("^(.*)(\\.)(rar|bz2|tgz|tar|gz|zip|bz|json|txt|js|py|md)$", link)
            if x:
                download.append(link)
        
        return(download)
    
    @classmethod
    def repository(self, tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the repositories of the tool.
        - tool: tool to be transformed
        '''
        repos = []
        if tool['repos'][0].get('kind')=='github':
            repos.append({
                    'url': f"https://github.com/{tool['repos'][0]['res'].get('owner')}/{tool['repos'][0]['res'].get('repo')}",
                    'kind': 'github',
                    'source_hasAnonymousAccess' : tool['repos'][0]['res'].get('source_hasAnonymousAccess', None),
                    'source_isDownloadRegistered' : tool['repos'][0]['res'].get('source_isDownloadRegistered', None),
                    'source_isFree' : tool['repos'][0]['res'].get('source_isFree', None),
                    'source_isRepoAccessible' : tool['repos'][0]['res'].get('source_isRepoAccessible', None)
                })
            
        elif tool['repos'].get('kind')=='bitbucket':
            repos.append({
                'url': f"https://bitbucket.org/{tool['repos'][0]['res'].get('owner')}/{tool['repos'][0]['res'].get('repo')}",
                'kind': 'bitbucket',
                'source_hasAnonymousAccess' : tool['repos'][0]['res'].get('source_hasAnonymousAccess', None),
                'source_isDownloadRegistered' : tool['repos'][0]['res'].get('source_isDownloadRegistered', None),
                'source_isFree' : tool['repos'][0]['res'].get('source_isFree', None),
                'source_isRepoAccessible' : tool['repos'][0]['res'].get('source_isRepoAccessible', None)
            })
            
        elif tool['repos'].get('kind')=='gitlab':
            repos.append({ 
                'url':f"https://gitlab.com/{tool['repos'][0]['res'].get('owner')}/{tool['repos'][0]['res'].get('repo')}",
                'kind': 'gitlab',
                'source_hasAnonymousAccess' : tool['repos'][0]['res'].get('source_hasAnonymousAccess', None),
                'source_isDownloadRegistered' : tool['repos'][0]['res'].get('source_isDownloadRegistered', None),
                'source_isFree' : tool['repos'][0]['res'].get('source_isFree', None),
                'source_isRepoAccessible' : tool['repos'][0]['res'].get('source_isRepoAccessible', None)
            })

        return(repos)
    
    @classmethod
    def documentation(self, tool: Dict[str, Any]) -> List[str]:
        
        if tool['repos'][0]['res'].get('readmeFile'):
            owner = tool['repos'][0]['res'].get('owner')
            repository = tool['repos'][0]['res'].get('repo')
            readme = tool['repos'][0]['res'].get('readmeFile')
            return [{
                'type': 'readme',
                'url': f"https://github.com/{owner}/{repository}/blob/master/{readme}"
            }]
        
        return []
    
    @classmethod
    def description(self, tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the description of the tool.
        - tool: tool to be transformed
        '''
        if tool['repos'][0]['res'].get('desc'):
            return([tool['repos'][0]['res'].get('desc')])
        else:
            return([])
        
    @classmethod
    def license(self, tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the license of the tool.
        - tool: tool to be transformed
        '''
        if tool['repos'][0]['res'].get('source_license'):
            return([{
                'name': tool['repos'][0]['res'].get('source_license'),
                'url': tool['repos'][0]['res'].get('source_license_uri')
            }])
        else:
            return([])
    

    @classmethod
    def authors(self, tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the authors of the tool.
        - tool: tool to be transformed
        '''
        authors = []
        authors_l = tool['repos'][0]['res'].get('tool_developers')
        if authors_l:
            for author in authors_l:
                if author.get('username', None):
                    authors.append({
                        'name': author.get('username', None),
                        'url': f"https://github.com/{author.get('username')}",
                        'type': 'Person'
                    })
                elif author.get('name', None):
                    authors.append({
                        'name': author.get('name', None),
                        'type': 'Person'
                    })
                elif author.get('company', None):
                    authors.append({
                        'url': f"https://github.com/{author.get('company', None)}",
                        'type': 'Organization',
                        'name': author.get('company', None)
                    })
        
        print(authors)
        
        return(authors)
    
    @classmethod
    def source_code(self, tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the source code of the tool.
        - tool: tool to be transformed
        '''
        source_code = []
        if tool['repos'][0]['res'].get('source_uri'):
            source_code.append(tool['repos'][0]['res'].get('source_uri'))
        
        return(source_code)

            
    def transform_single_tool(self, tool):
        '''
        Transforms a single tool into an instance.
        - tool: metadata of tool to be transformed
        '''
        
        id_data = self.get_repo_name_version_type(tool.get('@id'))
        name = self.clean_name(id_data['name'].lower())
        version = id_data['version']
        types_ = self.types(tool, name, id_data['type'])

        version = self.version(tool, version)
        download = self.download(tool)
        repository = self.repository(tool)
        webpage = [ tool['repos'][0]['res'].get('website') ]
        source = [tool['repos'][0]['kind']]
        description = self.description(tool)
        source_code = self.source_code(tool)
        languages = tool['repos'][0]['res'].get('languages', [])
        inst_instr = tool['repos'][0]['res'].get('has_tutorial', False)
        authors = self.authors(tool)
        license = self.license(tool)

        for type_ in types_: 
    
            new_instance = instance(
                name = name,
                type = type_,
                version = version,
                download = download,
                webpage = webpage,
                source = source,
                description = description,
                repository = repository,
                source_code = source_code,
                languages = languages,
                inst_instr = inst_instr,
                authors = authors,
                license = license
                )
            
        
            self.instSet.instances.append(new_instance)

    
    def transform(self, ignore_empty_bioconda_types = False):
        '''
        Performs the transformation of the raw metadata of tools into instances (homogenized and standardized).
            - ignore_empty_bioconda_types: if True, the transformation is performed even if the bioconda_types dictionary is empty.
        '''
        if ignore_empty_bioconda_types == False:
            if self.bioconda_types == {}:
                logging.error('bioconda_types is empty, aborting transformation')
                raise Exception('bioconda_types is empty, aborting transformation')
            
        for tool in self.tools:
            # We skip generic entries
            if len(tool['@id'].split('/'))<7:
                continue

            
            try:
                self.transform_single_tool(tool)
            except Exception as e:
                logging.error(f"Error transforming tool {tool['@id']}: {e}")
                continue