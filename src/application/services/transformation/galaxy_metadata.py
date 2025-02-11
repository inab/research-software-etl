from src.application.services.transformation.metadata_standardizers import MetadataStandardizer
from src.domain.models.software_instance.main import instance
from src.shared.utils import validate_and_filter

# --------------------------------------------
# Galaxy Metadata Metadata Standardizer
# --------------------------------------------

class galaxyMetadataStandardizer(MetadataStandardizer):
    def __init__(self, source = 'galaxy_metadata'):
        MetadataStandardizer.__init__(self, source)

    @classmethod
    def transform_one(cls, tool, standardized_tools):
        '''
        Transforms a single tool into an instance.
        '''
        tool = tool.get('data')
        
        if tool.get('id'):
            name = cls.clean_name(tool.get('id')).lower()
            version = [tool.get('version')]
            type_ = 'cmd'
            label = [tool.get('name')]
            dependencies = tool.get('dependencies')
            source = ['galaxy_metadata']

            new_instance_dict = {
                "name" : name,
                "type" : type_,
                "version" : version,
                "label" : label,
                "dependencies" : dependencies,
                "source" : source
            }

            # We keep only the fields that pass the validation
            new_instance = validate_and_filter(instance, **new_instance_dict)

            standardized_tools.append(new_instance)
            return standardized_tools

        else:
            return standardized_tools

