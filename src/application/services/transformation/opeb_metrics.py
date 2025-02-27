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
        - _id: id of the tool in OpenEBench. Exmaple: https://openebench.bsc.es/monitor/metrics/biotools:trimal:2.0-RC/cmd/trimal.cgenomics.org
        '''
        id_data = {}
        id_items = _id.split('/') # ['https:', '', 'openebench.bsc.es', 'monitor', 'metrics', 'biotools:trimal:2.0-RC', 'cmd', 'trimal.cgenomics.org']
        if len(id_items) > 6:
            source_name_version = id_items[5].split(':')
            id_data['name'] = source_name_version[1]
            if len(source_name_version) > 2:
                id_data['version'] = source_name_version[2]
            else:
                id_data['version'] = None
            
            id_data['type'] = id_items[6]

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
        if id_data:
            name = id_data.get('name')
            version = [id_data.get('version')]
            type_ = id_data.get('type')
            source = ['opeb_metrics']            
            
            new_instance = instance(
                name = name,
                type = type_,
                version = version,
                source = source,
                )
            
            standardized_tools.append(new_instance)
        
        return standardized_tools
