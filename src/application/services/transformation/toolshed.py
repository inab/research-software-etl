from src.application.services.transformation.metadata_standardizers import MetadataStandardizer
from src.domain.models.software_instance.main import instance
from src.shared.utils import validate_and_filter, is_repository
from typing import Dict, Any
import logging
import bibtexparser

logger = logging.getLogger("rs-etl-pipeline")
# -----------------------------------------------------------
# Galaxy Config (from Toolshed) MetadataStandardizer
# -----------------------------------------------------------

class toolshedStandardizer(MetadataStandardizer):

    def __init__(self, source = 'toolshed'):
        MetadataStandardizer.__init__(self, source)
    
    # --------  Functions to format specific fields --------

    @staticmethod
    def description(tool: Dict[str, Any]):
        '''
        Returns the description of the tool.
        '''

        if tool.get('description'):
            description =  tool['description']
            if description:
                description = description.strip()
                if description:
                    return([description])
            
        else:
            return([])
        
    
    @classmethod
    def data_formats(cls, tool: Dict[str, Any], field: str):
        '''
        Returns the data formats of the tool (for input or output fileds).
        - tool: tool dictionary
        - field: 'inputs' or 'outputs'
        '''
        formats = []
        if tool.get('dataFormats'):
            if tool['dataFormats'].get(field):
                for format in tool['dataFormats'][field]:
                    formats.append({
                        'term': format,
                        'uri': None
                    })
                
                return(formats)
            
        return([])
            
    @classmethod
    def documentation(cls, tool: Dict[str, Any]):
        '''
        Returns the documentation of the tool.
        '''
        if tool.get('help'):
            return([{'type':'help', 'url': None, 'content': tool['help']}])
        else:
            return([])
        
    @classmethod
    def citation(cls, tool: Dict[str, Any]):
        '''
        Returns the citation of the tool.
        '''
        new_cits = []
        if tool.get('citation'):
            for cit in tool['citation']:
                if cit.get('type') != 'doi':
                    new_cits.extend(cls.parse_bibtex_any(cit['citation']))
            return(new_cits)
        else:
            return([])
        
    
    @classmethod
    def parse_bibtex_misc(cls, bibtex_string):
        '''
        Gets any kind of information from bibtex citation.
        '''
        parser = bibtexparser.bparser.BibTexParser(common_strings=True)
        logger_bibtex = logging.getLogger('bibtexparser')
        new_entries = []
        try:
            bibtexdb = bibtexparser.loads(bibtex_string, parser=parser)
            for entry in bibtexdb.entries:
                if entry['ENTRYTYPE'].lower() == 'misc':
                    single_entry = {}
                    for key in entry:
                        single_entry[key] = entry[key]

                    new_entries.append(single_entry)
        except Exception as err:
            logger.error(f'FAILED attempt to parse citation (bibtex). Error: {err}')
        
        return(new_entries)
    
        
    @classmethod
    def repository(cls, tool: Dict[str, Any]):
        """
        Looks for a GitHub repository in the citation of the tool.
        """
        if not tool.get('citation'):
            return []

        for citation in tool['citation']:
            if citation.get('type') != 'bibtex':
                continue

            print(f"\bCitation: {citation}")

            parsed_citation = cls.parse_bibtex_misc(citation['value'])
            for item in parsed_citation:
                for key in ['url', 'crossref']:
                    repository = is_repository(item.get(key))
                    if repository:
                        return [ repository ]

        return []
    
    # --------  Main Function  --------
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
            description = cls.description(tool)
            test = tool.get('tests', False)
            input = cls.data_formats(tool, 'inputs')
            output = cls.data_formats(tool, 'outputs')
            documentation = cls.documentation(tool)
            #citation = self.citation(tool)
            operating_system = ['Linux', 'macOS']
            source = ['toolshed']
            repository = cls.repository(tool)

            new_instance_dict = {
                "name" : name,
                "type" : type_,
                "version" : version,
                "source" : source,
                "label" : label,
                "description" : description,
                "documentation" : documentation,
                "operating_system" : operating_system,
                "test" : test,
                "input" : input,
                "output" : output,
                "repository" : repository
            }
                
            # We keep only the fields that pass the validation
            new_instance = validate_and_filter(instance, **new_instance_dict)
            standardized_tools.append(new_instance)
            return standardized_tools

        else:
            return standardized_tools
    
    
    