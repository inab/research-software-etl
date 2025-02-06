from src.application.services.transformation.metadata_standardizers import MetadataStandardizer
from src.domain.models.software_instance.main import instance, setOfInstances

import logging 

# --------------------------------------------
# Galaxy Metadata Metadata Standardizer
# --------------------------------------------

class galaxyMetadataStandardizer(MetadataStandardizer):
    def __init__(self, source = 'galaxy_metadata'):
        MetadataStandardizer.__init__(self, source)

    def transform_one(self, tool, standardized_tools):
        '''
        Transforms a single tool into an instance.
        '''
        tool = tool.get('data')
        
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
                
            standardized_tools.append(new_instance)
            return standardized_tools

        else:
            return standardized_tools

