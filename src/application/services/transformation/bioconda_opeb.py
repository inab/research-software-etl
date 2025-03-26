from pydantic import HttpUrl, ValidationError
from typing import List, Dict, Any
from src.application.services.transformation.metadata_standardizers import MetadataStandardizer
from src.domain.models.software_instance.main import instance
from src.shared.utils import validate_and_filter

# --------------------------------------------
# Bioconda OPEB Metadata Standardizer
# --------------------------------------------


class biocondaOPEBStandardizer(MetadataStandardizer):

    def __init__(self, source = 'bioconda'):
        MetadataStandardizer.__init__(self, source)
    
    @staticmethod
    def get_name_version_type(id_):
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
    
    def types( self, name: str):
        '''
        NOT USED, but kept for future reference
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
    
    @staticmethod
    def description(tool: Dict[str, Any]):
        '''
        Returns the description of the tool.
        - tool: tool to be transformed
        '''
        description = tool.get('description')

        if description:
            return([description])
        
        else:
            return []        
        
    @staticmethod
    def webpage(tool: Dict[str, Any]):
        '''
        Returns the webpage of the tool.
        - tool: tool to be transformed
        '''
        if tool.get('web'):
            if tool['web'].get('homepage'):
                return([tool['web']['homepage']])
            
        else:
            return []
        
    @staticmethod
    def publication(tool: Dict[str, Any]):
        '''
        Returns the publication of the tool.
        - tool: tool to be transformed
        '''
        if tool.get('publications'):
            return(tool['publications'])
        
        else:
            return []
    
    @staticmethod
    def source_code(tool: Dict[str, Any]):
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
    
    @staticmethod
    def download(tool: Dict[str, Any]):
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

            documentation.append({
                'type': 'general',
                'url': f"https://bioconda.github.io/recipes/{tool['name']}/README.html"
            })


        
        return(documentation)
    
    @staticmethod
    def license(tool: Dict[str, Any]):
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
    
    @staticmethod
    def validate_http_url(url: str) -> bool:
        '''
        Validates an HTTP URL.
        - url: url to be validated
        '''
        try:
            validated_url = HttpUrl(url)
            return True
        except ValidationError as e:
            return False
    
    @staticmethod
    def repositories(tool: Dict[str, Any]):
        '''
        Returns the repositories of the tool.
        - tool: tool to be transformed
        '''
        repositories = []
        if tool.get('repositories'):
            for repo in tool['repositories']:
                if biocondaOPEBStandardizer.validate_http_url(repo):
                    repositories.append({
                        'url': repo
                    })
            
        return(repositories)
    
    
    @classmethod
    def transform_one(cls, tool, standardized_tools):
        '''
        Transforms a single tool into an instance.
        '''
        if len(tool['data'].get('@id').split('/'))<7:
            return []

        else:
            tool = tool.get('data')
            
            id_data = cls.get_name_version_type(tool.get('@id'))
            name = cls.clean_name(id_data['name'].lower())
            version = [ id_data['version'] ]
            type_ = id_data['type'] 
            source = ['bioconda']
            label = cls.clean_name(tool.get('@label'))
            description = cls.description(tool)
            webpage = cls.webpage(tool)
            publication = cls.publication(tool)
            download = cls.download(tool)
            source_code = cls.source_code(tool)
            documentation = cls.documentation(tool)
            license = cls.license(tool)
            repository = cls.repositories(tool)
            operating_system = ['Linux', 'macOS', 'Windows']

            

            new_instance_dict = {
                "name" : name,
                "type" : type_,
                "version" : version,
                "source" : source,
                "download" : download,
                "label" : label,
                "description" : description,
                "publication" : publication,
                "source_code" : source_code,
                "license" : license,
                "documentation" : documentation,
                "operating_system" : operating_system,
                "repository" : repository,
                "webpage" : webpage,
            }
            
            # We keep only the fields that pass the validation
            new_instance = validate_and_filter(instance, **new_instance_dict)
            
            standardized_tools.append(new_instance)
            
            return standardized_tools


