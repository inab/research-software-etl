from src.application.services.transformation.metadata_standardizers import MetadataStandardizer
from src.domain.models.software_instance.main import instance

from typing import List, Dict, Any

# --------------------------------------------
# OPEB Metrics Metadata Standardizer
# --------------------------------------------


class OPEBMetricsStandardizer(MetadataStandardizer):
    def __init__(self, source = 'opeb_metrics'):
        MetadataStandardizer.__init__(self, source)

    
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


    def extract_from_id(self, _id):
        '''
        Extracts the name and version from the id of the tool.
        - _id: id of the tool
        '''
        if len(_id.split('/')) < 3:
            raise Exception(f"Error extracting ids from {_id}")
        elif len(_id.split('/')) == 6:
            id_data = {
                'name': _id.split('/')[-1],
                'version': _id.split('/')[-2],
                'type': None,
            }
        else:
            id_data = self.extract_ids(_id)

        return(id_data)
    
    
    def transform_one(self, tool, standardized_tools):
        '''
        Transforms a single tool from oeb bio.tools into an instance.
        - tool: metadata of tool to be transformed
        - standardized_tools: list of standardized tools. To be appended with the new instance.
    
        * label is not present in the metadata. Since there must be a 
        document from OPEB tools with it, we will not try to guess a label
        using the name here.
        * since the URL of the website that fields like "ssl" refers to, is not gathered here
        '''

        tool = tool.get('data', {})

        id_data = self.extract_from_id(tool.get('@id'))
        name = self.clean_name(id_data.get('name')).lower()
        version = [id_data.get('version')]
        types_ = id_data.get('type')
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
            
            standardized_tools.append(new_instance)
        
        return standardized_tools
