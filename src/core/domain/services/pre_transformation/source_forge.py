from FAIRsoft.transformation.utils import toolGenerator
from FAIRsoft.classes.main import setOfInstances
from FAIRsoft.classes.main import instance

from typing import List, Dict, Any
import logging

# --------------------------------------------
# SourceForge Tools Transformer
# --------------------------------------------

class sourceforgeToolsGenerator(toolGenerator):
    def __init__(self, tools, source = 'sourceforge'):
        toolGenerator.__init__(self, tools, source)

        self.instSet = setOfInstances('sourceforge')

        self.transform()
    
    @classmethod
    def description(self, tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the description of the tool.
        - tool: metadata of tool to be transformed
        '''
        if tool.get('description'):
            return(tool['description'])
        else:
            return([])
        
    @classmethod
    def webpage(self, tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the webpage of the tool.
        - tool: metadata of tool to be transformed
        '''
        if tool.get('homepage'):
            return(tool['homepage'])
        else:
            return([])
        
    @classmethod
    def repository(self, tool: Dict[str, Any]) -> List[str]:
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
        
    @classmethod
    def license(self, tool: Dict[str, Any]) -> List[str]:
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
        
    @classmethod
    def operating_systems(self, tool: Dict[str, Any]) -> List[str]:
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

    def transform_single_tool(self, tool):
        '''
        Transforms a single tool into an instance.
        - tool: metadata of tool to be transformed
        '''
        
        name = tool.get('@source_url').split('/')[-1].lower()
        version = []
        label = [name]
        source = ['sourceforge']
        operating_systems = self.operating_systems(tool)
        description = self.description(tool)
        license = self.license(tool)
        repository = self.repository(tool)
        webpage =  [ self.webpage(tool) ]
        download = [tool.get('@source_url')]

        new_instance = instance(
            name = name,
            version = version,
            label = label,
            source = source,
            description = description,
            operating_system = operating_systems,
            repository = repository,
            webpage = webpage,
            download = download,
            license = license
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