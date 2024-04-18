from src.core.domain.services.transformation.metadata_standardizers import MetadataStandardizer
from src.core.domain.entities.software_instance.main import instance
from src.core.domain.entities.software_instance.EDAM_forFE import EDAMDict

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
    def __init__(self, source = 'biotoolsOPEB', ignore_empty_bioconda_types = False):
        MetadataStandardizer.__init__(self, source, ignore_empty_bioconda_types)
    
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
    def documentation(self, tool):
        '''
        Reformat the documentation field. 
        The url cannot be empty, so if it is, it is not added to the documentation list.
        '''
        documentation = []
        if tool.get('documentation'):
            for key in tool['documentation'].keys():
                if tool['documentation'][key]:
                    documentation.append({
                        'type': key,
                        'url': tool['documentation'][key]            
                    })
        return(documentation)

    @classmethod
    def topics_operations(self, items):
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


    @classmethod
    def license(self, tool):
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
        else:
            return []

    @classmethod
    def data_format_item(self, data: Dict[str, Any]):
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
        
    @classmethod
    def data_format(self, items):
        '''
        Performs the reformat of the input and output field.
        '''
        new_items = []
        for item in items:
            new_item = self.data_format_item(item)
            if new_item:
                new_items.extend(new_item)
        return(new_items)
    
    @classmethod
    def empty_string_to_none(self, data):
        '''
        If the string is empty, turn it into None.
        '''
        if data == '':
            return None
        else:
            return data
        
    @classmethod
    def label(self, tool: Dict[str, Any]):
        '''
        If name does not exist, use label instead.
        '''
        name = self.clean_name(tool['name'])
        if name:
            return([name])
        else:
            return([tool['@label']])
    
    @classmethod
    def webpage(self, tool: Dict[str, Any]):
        '''
        If the webpage is empty, return None.
        '''
        try:
            if tool['web']['homepage'] == '':
                pass
        except:
            return []
        else:
            return [tool['web']['homepage']]
    
    @classmethod
    def description(self, tool: Dict[str, Any]):
        if tool.get('description'):
            return [tool['description']]
        else:
            return []
        

    @classmethod
    def repositories(self, tool: Dict[str, Any]):
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

        
    def transform_one(self, tool, standardized_tools):
        '''
        Transforms a single tool from oeb bio.tools into an instance.
        '''
        self.check_bioconda_types_empty()

        tool = tool.get('data')

        name = self.clean_name(tool.get('@label')).lower()
        type = self.type(name = name, _id = tool['@id'], type_ = tool['@type'])
        version = [ tool['@version'] ]
        source = ['biotools']
        label = self.label(tool)
        description = self.description(tool)
        publication = tool.get('publications',[])
        test = False
        license = self.license(tool)
        documentation = self.documentation(tool)
        os = tool.get('os', [])
        repository = self.repositories(tool)
        webpage = self.webpage(tool)
        if tool.get('semantics'):
            input = self.data_format(tool['semantics'].get('inputs', []))
            output = self.data_format(tool['semantics'].get('outputs', []))
            topics = self.topics_operations(tool['semantics']['topics'])
            operations = self.topics_operations(tool['semantics']['operations'])
        else:
            input = []
            output = []
            topics = []
            operations = []

        authors = tool.get('credits',[])
        tags = tool.get('tags',[])
        
    
        new_instance = instance(
            name = name,
            type = type,
            version = version,
            source = source,
            label = label,
            description = description,
            publication = publication,
            test = test,
            license = license,
            documentation = documentation,
            operating_system = os,
            repository = repository,
            webpage = webpage,
            input = input,
            output = output,
            topics = topics,
            operations = operations,
            authors = authors,
            tags = tags
            )

        standardized_tools.append(new_instance)
    
        return standardized_tools
    

            