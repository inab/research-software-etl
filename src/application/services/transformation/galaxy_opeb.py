from src.application.services.transformation.metadata_standardizers import MetadataStandardizer
from src.domain.models.software_instance.main import instance
from src.shared.utils import validate_and_filter

from typing import List, Dict, Any

# --------------------------------------------
# Galaxy OPEB Metadata Standardizer
# --------------------------------------------

class galaxyOPEBStandardizer(MetadataStandardizer):
    def __init__(self, source = 'galaxy'):
        MetadataStandardizer.__init__(self)
    
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
        

    @staticmethod
    def webpage(tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the webpage of the tool.
        - tool: metadata of tool to be transformed
        '''
        webpage = []
        if tool.get('web'):
            if tool['web'].get('homepage'):
                webpage.append(tool['web']['homepage'])
        
        return(webpage)

    @classmethod
    def transform_one(cls, tool, standardized_tools):
        '''
        Transforms a single tool into an instance.
        - tool: metadata of tool to be transformed
        '''
        tool = tool.get('data')
        
        name = cls.clean_name(tool.get('@label')).lower()
        version = [tool.get('@version')]
        type_ = 'cmd'
        label = [tool.get('name')]
        description = cls.description(tool)
        source = ['galaxy']
        operating_systems = ['macOS', 'Linux']
        webpage = cls.webpage(tool)
    
        new_instance_dict = {
            "name" : name,
            "type" : type_,
            "version" : version,
            "label" : label,
            "source" : source,
            "description" : description,
            "operating_systems" : operating_systems,
            "webpage" : webpage
        }
            
        # We keep only the fields that pass the validation
        new_instance = validate_and_filter(instance, **new_instance_dict)

        standardized_tools.append(new_instance)

        return standardized_tools

