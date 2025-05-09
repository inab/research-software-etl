from src.application.services.transformation.metadata_standardizers import MetadataStandardizer
from src.domain.models.software_instance.main import instance
from src.domain.models.software_instance.EDAM_forFE import EDAMDict
from src.shared.utils import validate_and_filter

from pydantic import TypeAdapter, HttpUrl, BaseModel, model_validator
from typing import List, Dict, Any

# --------------------------------------------
# Biotools OPEB Tools Transformer
# --------------------------------------------


# BIO.TOOLS FORMAT  ----------------------------------------------
class biotools_data_format(BaseModel, validate_assignment=True):
    '''
    Example:
        {
            "datatype" : "http://edamontology.org/data_2610",
            "formats" : []
        }
    '''
    datatype: HttpUrl = None
    formats: List[HttpUrl] = []

    @model_validator(mode="before")
    @classmethod
    def at_least_one_field(cls, data: Dict[str, Any]):
        '''
        !! At least one of the fields must be present
        '''
        if 'datatype' not in data and 'formats' not in data:
            raise ValueError("At least one of the fields 'datatype' or 'formats' must be present")
        else:
            return data

# bio.tools metadata standardizer subclass --------------------------------------------
class biotoolsOPEBStandardizer(MetadataStandardizer):
    def __init__(self, source = 'biotoolsOPEB'):
        MetadataStandardizer.__init__(self, source)
    

    @staticmethod
    def documentation(tool):
        '''
        Reformat the documentation field. 
        The url cannot be empty, so if it is, it is not added to the documentation list.
        '''
        documentation = []
        if tool.get('documentation'):
            # Links without classification. They are a list under the key 'doc_links'
            if tool['documentation'].get('doc_links') and len(tool['documentation']['doc_links']) > 0:
                for url in tool['documentation']['doc_links']:
                    if url:
                        documentation.append({
                            'type': 'general',
                            'url': url
                        })

            # Diferent kinds of documentation. They are different keys in documentation
            for key in tool['documentation'].keys():
                if key != 'doc_links' and tool['documentation'][key]:
                    documentation.append({
                        'type': key,
                        'url': tool['documentation'][key]            
                    })
        return(documentation)

    @staticmethod
    def topics_operations(items):
        '''
        Reformat edam_topics and edam_operations fields.
        - tool: the tool dictionary.
        - field: the field to reformat ('edam_topics' or 'edam_operations').
        '''
        new_items = []
        for item in items:
            new_item = {
                'uri' : item
            }
            new_items.append(new_item)
                    
        return(new_items)


    @staticmethod
    def license(tool):
        '''
        Builds a dictionary for the licenses.
        '''
        value = tool.get('license')
        if isinstance(value, List):
            items = []
            for item in value:
                ta = TypeAdapter(HttpUrl)
                try:
                    ta.validate_strings(item)
                except:
                    new_item = {
                        'name': item,
                        "url": None
                    }
                else:
                    if isinstance(item, str):
                        new_item = {
                            'name': '',
                            "url": item
                        }
                    else:
                        continue
                
                items.append(new_item)

            return items
        elif isinstance(value, str):
            return [{
                'name': value,
                'url': None
            }]
        else:
            return []

    @staticmethod
    def data_format_item(data: Dict[str, Any]):
        '''
        Reformats each data format item coming from bio.tools
        '''
        
        try:
            obj = biotools_data_format.model_validate(data, strict=True)
        except:
            return data
        
        else:
            reformatted_items = []
            
            if 'datatype' in data:
                datatype = {
                    'vocabulary': 'EDAM',
                    'term': EDAMDict[data['datatype']],
                    'uri': data['datatype']
                }
            else:
                datatype = {}
            
            if 'formats' in data and data['formats']:
                for format in data['formats']:
                    new_format = {
                        'vocabulary': 'EDAM',
                        'term': EDAMDict[format],
                        'uri': format,
                        'datatype': datatype
                    }
                    reformatted_items.append(new_format)
            else:
                if datatype:
                    new_format = {
                        'datatype': datatype
                    }
                    reformatted_items.append(new_format)

            return reformatted_items
        
    @staticmethod
    def data_format(items):
        '''
        Performs the reformat of the input and output field.
        '''
        new_items = []
        for item in items:
            new_item = biotoolsOPEBStandardizer.data_format_item(item)
            if new_item:
                new_items.extend(new_item)
        return(new_items)
    
    @staticmethod
    def empty_string_to_none(data):
        '''
        If the string is empty, turn it into None.
        '''
        if data == '':
            return None
        else:
            return data
        
    @staticmethod
    def label(tool: Dict[str, Any]):
        '''
        If name does not exist, use label instead.
        '''
        name = biotoolsOPEBStandardizer.clean_name(tool['name'])
        if name:
            return([name])
        else:
            return([tool['@label']])
    
    @staticmethod
    def webpage(tool: Dict[str, Any]):
        """
        If the webpage is empty or not present, return an empty list.
        Otherwise, return a list containing the homepage URL.
        """
        try:
            # Safely attempt to access the homepage URL
            homepage = tool.get('web', {}).get('homepage', '')
            if not homepage:  # Covers both empty string and None
                return []
            return [homepage]
        except Exception as e:
            # Handle unexpected errors
            return []
        
    @staticmethod
    def description(tool: Dict[str, Any]):
        if tool.get('description'):
            return [tool['description']]
        else:
            return []
        

    @staticmethod
    def repositories(tool: Dict[str, Any]):
        '''
        Returns the repositories of the tool.
        - tool: tool to be transformed
        '''
        repositories = []
        if tool.get('repositories'):
            for repo in tool['repositories']:
                repositories.append({
                    'url': repo,
                })

        return(repositories)

    
    @classmethod
    def transform_one(cls, tool, standardized_tools):
        '''
        Transforms a single tool from oeb bio.tools into an instance.
        '''

        tool = tool.get('data')

        name = cls.clean_name(tool.get('@label')).lower()
        type = tool.get('@type')
        version = [ tool['@version'] ]
        source = ['biotools']
        label = cls.label(tool)
        description = cls.description(tool)
        test = False
        license = cls.license(tool)
        documentation = cls.documentation(tool)
        os = tool.get('os', [])
        repository = cls.repositories(tool)
        webpage = cls.webpage(tool)
        if tool.get('semantics'):
            input = cls.data_format(tool['semantics'].get('inputs', []))
            output = cls.data_format(tool['semantics'].get('outputs', []))
            topics = cls.topics_operations(tool['semantics']['topics'])
            operations = cls.topics_operations(tool['semantics']['operations'])
        else:
            input = []
            output = []
            topics = []
            operations = []

        authors = tool.get('credits',[])
        tags = tool.get('tags',[])
        links = tool.get('links', [])
        
    
        new_instance_dict = {
            "name" : name,
            "type" : type,
            "version" : version,
            "source" : source,
            "label" : label,
            "description" : description,
            "test" : test,
            "license" : license,
            "documentation" : documentation,
            "operating_system" : os,
            "repository" : repository,
            "webpage" : webpage,
            "input" : input,
            "output" : output,
            "topics" : topics,
            "operations" : operations,
            "authors" : authors,
            "tags" : tags,
            "links" : links
        
        }

        # We keep only the fields that pass the validation
        new_instance = validate_and_filter(instance, **new_instance_dict)

        standardized_tools.append(new_instance)
    
        return standardized_tools
    

            