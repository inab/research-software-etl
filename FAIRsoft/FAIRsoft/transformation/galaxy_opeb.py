from FAIRsoft.transformation.utils import toolGenerator
from FAIRsoft.classes.main import setOfInstances
from FAIRsoft.classes.main import instance

from typing import List, Dict, Any
import logging 

# --------------------------------------------
# Galaxy OPEB Tools Transformer
# --------------------------------------------

class galaxyOPEBToolsGenerator(toolGenerator):
    def __init__(self, tools, source = 'galaxy'):
        toolGenerator.__init__(self, tools, source)

        self.instSet = setOfInstances('galaxy')

        self.transform()
    
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

    def transform_single_tool(self, tool):
        '''
        Transforms a single tool into an instance.
        - tool: metadata of tool to be transformed
        '''
        
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
            
        
        self.instSet.instances.append(new_instance)

    def transform(self):
        '''
        Performs the transformation of the raw metadata of tools into instances (homogenized and standardized).
        '''
    
        for tool in self.tools:
            self.transform_single_tool(tool)
        '''
            try:
                self.transform_single_tool(tool)
            except Exception as e:
                logging.error(f"Error transforming tool {tool['@id']}: {e}")
                continue
                
        '''
    