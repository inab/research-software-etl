from src.core.domain.services.transformation.metadata_standardizers import MetadataStandardizer
from src.core.domain.entities.software_instance.main import instance

from typing import List, Dict, Any
import logging 

# --------------------------------------------
# Galaxy OPEB Metadata Standardizer
# --------------------------------------------

class galaxyOPEBStandardizer(MetadataStandardizer):
    def __init__(self, source = 'galaxy', ignore_empty_bioconda_types = False):
        MetadataStandardizer.__init__(self, source, ignore_empty_bioconda_types)
    
    @classmethod
    def description(self, tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the description of the tool.
        - tool: metadata of tool to be transformed
        '''
        if tool.get('description'):
            return([tool['description']])
        else:
            return([])
        

    @classmethod
    def webpage(self, tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the webpage of the tool.
        - tool: metadata of tool to be transformed
        '''
        webpage = []
        if tool.get('web'):
            if tool['web'].get('homepage'):
                webpage.append(tool['web']['homepage'])
        
        return(webpage)

    def transform_one(self, tool, standardized_tools):
        '''
        Transforms a single tool into an instance.
        - tool: metadata of tool to be transformed
        '''
        tool = tool.get('data')
        
        name = self.clean_name(tool.get('@label')).lower()
        version = [tool.get('@version')]
        type_ = 'cmd'
        label = [tool.get('name')]
        description = self.description(tool)
        source = ['galaxy']
        operating_systems = ['macOS', 'Linux']
        webpage = self.webpage(tool)

    
        new_instance = instance(
            name = name,
            type = type_,
            version = version,
            label = label,
            source = source,
            description = description,
            operating_systems = operating_systems,
            webpage = webpage
            )
            
        
        standardized_tools.append(new_instance)

        return standardized_tools

