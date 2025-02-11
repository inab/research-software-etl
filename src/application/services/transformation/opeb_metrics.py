from src.application.services.transformation.metadata_standardizers import MetadataStandardizer
from src.domain.models.software_instance.main import instance

from typing import List, Dict, Any

# --------------------------------------------
# OPEB Metrics Metadata Standardizer
# --------------------------------------------


class OPEBMetricsStandardizer(MetadataStandardizer):
    def __init__(self, source = 'opeb_metrics'):
        MetadataStandardizer.__init__(self, source)

    
    @staticmethod
    def bioschemas(tool: Dict[str, Any]) -> List[str]:
        '''
        Returns the bioschemas of the tool.
        - tool: tool to be transformed
        '''
        bioschemas = None
        if tool.get('project'):
            if tool['project'].get('website'):
                bioschemas = tool['project']['website'].get('bioschemas')

        return(bioschemas)
    
    @staticmethod
    def https(tool: Dict[str, Any]) -> List[str]:
        '''
        Returns https.
        - tool: tool to be transformed
        '''
        https = None
        if tool.get('project'):
            if tool['project'].get('website'):
                https = tool['project']['website'].get('https')

        return(https)
    
    @staticmethod
    def ssl(tool: Dict[str, Any]) -> List[str]:
        '''
        Returns ssl.
        - tool: tool to be transformed
        '''
        ssl = None
        if tool.get('project'):
            if tool['project'].get('website'):
                ssl = tool['project']['website'].get('ssl')
        
        return(ssl)
    
    @staticmethod
    def operational(tool: Dict[str, Any]) -> List[str]:
        '''
        Returns operational.
        - tool: tool to be transformed
        '''
        operational = None
        if tool.get('project'):
            if tool['project'].get('website'):
                operational = tool['project']['website'].get('operational')
        
        return(operational)
    

    @staticmethod
    def publications(tool: Dict[str, Any]) -> List[str]:
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

    @staticmethod
    def extract_from_id(_id):
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
            id_data = OPEBMetricsStandardizer.extract_ids(_id)

        return(id_data)
    
    
    @classmethod
    def transform_one(cls, tool, standardized_tools):
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

        id_data = cls.extract_from_id(tool.get('@id'))
        name = cls.clean_name(id_data.get('name')).lower()
        version = [id_data.get('version')]
        types_ = id_data.get('type')
        source = ['opeb_metrics']
        publication = cls.publications(tool)
        
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
