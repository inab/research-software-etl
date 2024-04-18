from src.core.domain.services.transformation.utils import MetadataStandardizer
from src.core.domain.entities.software_instance.main import setOfInstances
from src.core.domain.entities.software_instance.main import instance
from src.core.domain.entities.software_instance.EDAM_forFE import EDAMDict

from typing import List, Dict, Any
import logging

# --------------------------------------------
# Bioconda Tools Transformer
# --------------------------------------------


class biocondaOPEBStandardizer(MetadataStandardizer):

    def __init__(self, source = 'biocondaOPEB', ignore_empty_bioconda_types = False):
        MetadataStandardizer.__init__(self, source, ignore_empty_bioconda_types)
    
    @classmethod
    def get_repo_name_version_type(self, id_):
        fields = id_.split('/')
        name_plus = fields[5]
        name_plus_fields=name_plus.split(':')
        name=name_plus_fields[1]
        if len(name_plus_fields)>2:
            version=name_plus.split(':')[2]
        else:
            version=None 

        if len(fields)>6:
            type_=fields[6]
        else:
            type_=None
        
        return({'name':name, 'version':version, 'type':type_})
    
    def types(self, tool: Dict[str, Any], name: str, type_: str):
        '''
        Returns the types of the tool.
        - tool: tool to be transformed
        '''
        # We get the types from the bioconda_types dictionary
        if self.bioconda_types.get(name):
            types_ = [self.bioconda_types[name]]
        
        # If there is no type in bioconda_types, we assume cmd
        else:
            types_ = ['cmd']

        return(types_)
    
    @classmethod
    def description(self, tool: Dict[str, Any]):
        '''
        Returns the description of the tool.
        - tool: tool to be transformed
        '''
        description = tool.get('description')

        if description:
            return([description])
        
        else:
            return []        
        
    @classmethod
    def webpage(self, tool: Dict[str, Any]):
        '''
        Returns the webpage of the tool.
        - tool: tool to be transformed
        '''
        if tool.get('web'):
            if tool['web'].get('homepage'):
                return([tool['web']['homepage']])
            
        else:
            return []
        
    @classmethod
    def publication(self, tool: Dict[str, Any]):
        '''
        Returns the publication of the tool.
        - tool: tool to be transformed
        '''
        if tool.get('publications'):
            return(tool['publications'])
        
        else:
            return []
    
    @classmethod
    def source_code(self, tool: Dict[str, Any]):
        '''
        Returns the source code links of the tool.
        - tool: tool to be transformed
        Fields are 'source_packages' and 'sourcecode'
        '''
        source_code = []
        if tool.get('distributions'):
            for key in tool['distributions']:
                if 'source' in key and tool['distributions'].get(key):
                    for url in tool['distributions'][key]:
                        source_code.append(url)
        
        return(source_code)
    
    @classmethod
    def download(self, tool: Dict[str, Any]):
        '''
        Returns the download links of the tool.
        - tool: tool to be transformed
        '''
        download = []
        if tool.get('distributions'):
            for key in tool['distributions']:
                for url in tool['distributions'][key]:
                    download.append(url)
        
        return(download)
    
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
        
        return(documentation)
    
    @classmethod
    def license(self, tool: Dict[str, Any]):
        '''
        Returns the license of the tool.
        - tool: tool to be transformed
        '''
        license = []
        if tool.get('license'):
            license.append({
                'name': tool['license'],
                'url': None
            })
        
        return(license)
    
    @classmethod
    def repositories(self, tool: Dict[str, Any]):
        '''
        Returns the repositories of the tool.
        - tool: tool to be transformed
        '''
        repositories = []
        if tool.get('repositories'):
            for repo in tool['repositories']:
                repositories.append({
                    'url': repo
                })
        
        return(repositories)
    
    @classmethod
    def version(self, version):
        if version:
            if isinstance(version, str):
                return([version])
        
        return None
    

    def transform_single_tool(self, tool):
        '''
        Transforms a single tool into an instance.
        '''
        tool = tool.get('data')
        
        id_data = self.get_repo_name_version_type(tool.get('@id'))
        name = self.clean_name(id_data['name'].lower())
        version = [ id_data['version'] ]
        types = self.types(tool, name, id_data['type'])
        source = ['bioconda']
        label = self.clean_name(tool.get('@label'))
        description = self.description(tool)
        webpage = self.webpage(tool)
        publication = self.publication(tool)
        download = self.download(tool)
        source_code = self.source_code(tool)
        documentation = self.documentation(tool)
        license = self.license(tool)
        repository = self.repositories(tool)
        operating_system = operating_system = ['Linux', 'macOS', 'Windows']

        results = []

        for type_ in types:

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
                )
            
            results.append(new_instance)
        
        return results

    def transform_one(self, tool):
        '''
        Performs the transformation of the raw metadata of tools into instances (homogenized and standardized).
            - ignore_empty_bioconda_types: if True, the transformation is performed even if the bioconda_types dictionary is empty.
        '''
        if self.ignore_empty_bioconda_types == False:
            if self.bioconda_types == {}:
                logging.error('bioconda_types is empty, aborting transformation')
                raise Exception('bioconda_types is empty, aborting transformation')
            
        # We skip generic entries
        if len(tool['data'].get('@id').split('/'))>=7:
            try:
                standardized_tools = self.transform_single_tool(tool)
            except Exception as e:
                logging.error(f"Error transforming tool {tool['@id']}: {e}")
                return None
            else:
                return standardized_tools
        else:
            return None

