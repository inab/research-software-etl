from src.application.services.transformation.metadata_standardizers import MetadataStandardizer
from src.domain.models.software_instance.main import instance
from src.shared.utils import validate_and_filter

from typing import List, Dict, Any

# --------------------------------------------
# SourceForge Metadata Standardizer
# --------------------------------------------

class sourceforgeStandardizer(MetadataStandardizer):
    def __init__(self, source = 'sourceforge'):
        MetadataStandardizer.__init__(self, source)

    @staticmethod
    def description(tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the description of the tool.
        - tool: metadata of tool to be transformed
        '''
        if tool.get('description'):
            return(tool['description'])
        else:
            return([])
        
    @staticmethod
    def webpage(tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the webpage of the tool.
        - tool: metadata of tool to be transformed
        '''
        if tool.get('homepage'):
            return([tool['homepage']])
        else:
            return([])
        
    @staticmethod
    def repository(tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the repository of the tool.
        - tool: metadata of tool to be transformed
        '''
        repos = []
        if tool.get('repository'):
            repos.append({
                'url' : tool['repository']
                })
        elif tool.get('@source_url'):
            repos.append({
                'url' : tool['@source_url']
                })
        
        return(repos)
        
    @staticmethod
    def license(tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the license of the tool.
        - tool: metadata of tool to be transformed
        '''
        licenses = []
        if tool.get('license'):
            for license in tool['license']:
                licenses.append({
                    'name' : license,
                    'url' : None
                    })

        return(licenses)
        
    @staticmethod
    def operating_systems(tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the operating systems of the tool.
        - tool: metadata of tool to be transformed
        '''
        # some OS have spaces after or before the name, so we need to remove them
        operating_systems = []
        if tool.get('operating_systems'):
            for os in tool['operating_systems']:
                operating_systems.append(os.strip())

        return operating_systems

    @staticmethod
    def description(tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the description of the tool.
        - tool: metadata of tool to be transformed
        '''
        if tool.get('description'):
            return([tool['description']])
        else:
            return([])

    @classmethod
    def transform_one(cls, tool, standardized_tools):
        '''
        Transforms a single tool into an instance.
        - tool: metadata of tool to be transformed
        '''
        source_url = tool.get('@source_url')
        tool = tool.get('data')
        
        name = source_url.split('/')[-1].lower()
        version = []
        label = [name]
        source = ['sourceforge']
        operating_systems = cls.operating_systems(tool)
        description = cls.description(tool)
        license = cls.license(tool)
        repository = cls.repository(tool)
        webpage =   cls.webpage(tool)
        download = [source_url]

        new_instance_dict = {
            "name" : name,
            "version" : version,
            "label" : label,
            "source" : source,
            "description" : description,
            "operating_system" : operating_systems,
            "repository" : repository,
            "webpage" : webpage,
            "download" : download,
            "license" : license
        }
        
        # We keep only the fields that pass the validation
        new_instance = validate_and_filter(instance, **new_instance_dict)

        standardized_tools.append(new_instance)
        
        return standardized_tools
                