from FAIRsoft.transformation.utils import toolGenerator
from FAIRsoft.classes.main import setOfInstances
from FAIRsoft.classes.main import instance
from FAIRsoft.classes.EDAM_forFE import EDAMDict

from pydantic import TypeAdapter, HttpUrl, BaseModel, model_validator
from typing import List, Dict, Any
import logging 

# --------------------------------------------
# Galaxy Metadata Tools Transformer
# --------------------------------------------

class galaxyMetadataToolsGenerator(toolGenerator):
    def __init__(self, tools, source = 'galaxy_metadata'):
        toolGenerator.__init__(self, tools, source)

        self.instSet = setOfInstances('galaxy_metadata')

        self.transform()

    def transform_single_tool(self, tool):
        '''
        Transforms a single tool into an instance.
        '''
        if tool.get('id'):
            name = self.clean_name(tool.get('id')).lower()
            version = [tool.get('version')]
            type_ = 'cmd'
            label = [tool.get('name')]
            dependencies = tool.get('dependencies')
            source = ['galaxy_metadata']
        
            new_instance = instance(
                name = name,
                type = type_,
                version = version,
                label = label,
                dependencies = dependencies,
                source = source
                )
                
            
            self.instSet.instances.append(new_instance)

        else:
            pass

    def transform(self):
        '''
        Performs the transformation of the raw data into instances.
        '''
        for tool in self.tools:
            try:
                self.transform_single_tool(tool)
            except Exception as e:
                logging.error(f"Error transforming tool {tool['@id']}: {e}")
                continue
    