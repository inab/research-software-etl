from FAIRsoft.transformation.utils import toolGenerator
from FAIRsoft.classes.main import setOfInstances
from FAIRsoft.classes.main import instance

from typing import List, Dict, Any
import logging 


# --------------------------------------------
# OPEB Metrics Tools Transformer
# --------------------------------------------


class OPEBMetricsToolsGenerator(toolGenerator):
    def __init__(self, tools, source = 'opeb_metrics'):
        toolGenerator.__init__(self, tools, source)

        self.instSet = setOfInstances('opeb_metrics')

        self.transform()

    @classmethod
    def type(self, name, _id, type_):
        '''
        This function returns the type of the tool.
        If the tool is in bioconda, it returns the type of the bioconda tool, since it is more reliable.
        If the tool is a workflow, it returns cmd.
        '''
        if self.bioconda_types.get(name):
                types_ = self.bioconda_types[name]
        elif type_ == 'workflow' and 'galaxy' in _id:
            types_='cmd'
        else:
            types_ = type_

        return(types_)
    
    @classmethod
    def bioschemas(self, tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the bioschemas of the tool.
        - tool: tool to be transformed
        '''
        bioschemas = None
        if tool.get('project'):
            if tool['project'].get('website'):
                bioschemas = tool['project']['bioschemas'].get('bioschemas')

        return(bioschemas)
    
    @classmethod
    def https(self, tool: Dict[str, Any]) -> List[str]:
        '''
        Returns https.
        - tool: tool to be transformed
        '''
        https = None
        if tool.get('project'):
            if tool['project'].get('website'):
                https = tool['project']['website'].get('https')

        return(https)
    
    @classmethod
    def ssl(self, tool: Dict[str, Any]) -> List[str]:
        '''
        Returns ssl.
        - tool: tool to be transformed
        '''
        ssl = None
        if tool.get('project'):
            if tool['project'].get('website'):
                ssl = tool['project']['website'].get('ssl')
        
        return(ssl)
    
    @classmethod
    def operational(self, tool: Dict[str, Any]) -> List[str]:
        '''
        Returns operational.
        - tool: tool to be transformed
        '''
        operational = None
        if tool.get('project'):
            if tool['project'].get('website'):
                operational = tool['project']['website'].get('operational')
        
        return(operational)
    

    @classmethod
    def publications(self, tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the publications of the tool.
        - tool: tool to be transformed
        '''
        publications = []
        if tool.get('project'):
            if tool['project'].get('publications'):
                for publication in tool['project']['publications']:
                    publications.extend(publication.get('entries', []))
        
        return(publications)

    
    
    def transform_single_tool(self, tool):
        '''
        Transforms a single tool from oeb bio.tools into an instance.
        - tool: metadata of tool to be transformed

        * label is not present in the metadata. Since there must be a 
        document from OPEB tools with it, we will not try to gress a label
        using the name here.
        * since the URL of the website that fields like "ssl" refers to, is not gathered here
        '''
        id_data = self.extract_ids(tool['@id'])
        name = self.clean_name(id_data.get('name')).lower()
        version = id_data.get('version')
        types_ = self.types(tool, name, id_data.get('type'))
        source = ['opeb_metrics']
        publication = self.publications(tool)
        
        for type_ in types_:
            new_instance = instance(
                name = name,
                type = type_,
                version = version,
                source = source,
                publication = publication
                )
            
            self.instSet.instances.append(new_instance)


    def transform(self, ignore_empty_bioconda_types = False):
        '''
        Performs the transformation of the raw data into instances.
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
            