from core.domain.services.transformation.metadata_standardizers import MetadataStandardizer
from src.core.domain.entities.software_instance.main import instance

from typing import Dict, Any
import logging
import json
import bibtexparser

# -------------------------------------------------
# Galaxy Config (from Toolshed) MetadataStandardizer
# -------------------------------------------------

class toolshedStandardizer(MetadataStandardizer):

    def __init__(self, source = 'toolshed', ignore_empty_bioconda_types = False):
        MetadataStandardizer.__init__(self, source, ignore_empty_bioconda_types)

    
    def description(self, tool: Dict[str, Any]):
        '''
        Returns the description of the tool.
        '''
        if tool.get('description'):
            return(tool['description'])
        else:
            return([])
        

    @staticmethod
    def parse_bibtex(ent):
        '''
        Gets journal publication information from bibtex citation.
        '''
        parser = bibtexparser.bparser.BibTexParser(common_strings=True)
        logger = logging.getLogger('bibtexparser')
        new_entries = []
        try:
            bibtexdb = bibtexparser.loads(ent, parser=parser)
            for entry in bibtexdb.entries:
                if entry['ENTRYTYPE'].lower() != 'misc':
                    #print(entry)
                    single_entry = {}
                    single_entry['url'] = entry.get('url')
                    single_entry['title'] = entry.get('title')
                    single_entry['year'] = entry.get('year')
                    single_entry['journal'] = entry.get('journal')
                    single_entry['doi'] = entry.get('doi')
                    single_entry['pmid'] = entry.get('pmid')
                    new_entries.append(single_entry)
        except Exception as err:
            logger.error(f'FAILED attempt to parse citation (bibtex). Error: {err}')
            logger.error(json.dumps(ent, sort_keys=False, indent=4))

        return(new_entries)
    
    @classmethod
    def parse_bibtex_any(self, ent):
        '''
        Gets any kind of information from bibtex citation.
        '''
        parser = bibtexparser.bparser.BibTexParser(common_strings=True)
        logger = logging.getLogger('bibtexparser')
        new_entries = []
        
        
        bibtexdb = bibtexparser.loads(ent, parser=parser)
        for entry in bibtexdb.entries:
            if entry['ENTRYTYPE'].lower() == 'misc':
                single_entry = {}
                for key in entry:
                    single_entry[key] = entry[key]

                new_entries.append(single_entry)
        '''
        except Exception as err:
            logger.error(f'FAILED attempt to parse citation (bibtex). Error: {err}')
            logger.error(json.dumps(ent, sort_keys=False, indent=4))
        '''
        
        return(new_entries)
    
    def publication(self, tool: Dict[str, Any]):
        '''
        Returns the publication of the tool.
        '''
        new_pubs = []
        if tool.get('citation'):
            for cit in tool['citation']:
                if cit.get('type') == 'doi':
                    new_pub = {'doi':cit.get('citation')}
                    new_pubs.append(new_pub)
                else:
                    new_entries = toolshedStandardizer.parse_bibtex(cit.get('citation'))
                    for se in new_entries:
                        new_pubs.append(se)
        
        return(new_pubs)
    
    @classmethod
    def data_formats(self, tool: Dict[str, Any], field: str):
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
    def documentation(self, tool: Dict[str, Any]):
        '''
        Returns the documentation of the tool.
        '''
        if tool.get('help'):
            return([{'type':'help', 'url': None, 'content': tool['help']}])
        else:
            return([])
        
    @classmethod
    def citation(self, tool: Dict[str, Any]):
        '''
        Returns the citation of the tool.
        '''
        new_cits = []
        if tool.get('citation'):
            for cit in tool['citation']:
                if cit.get('type') != 'doi':
                    new_cits.extend(self.parse_bibtex_any(cit['citation']))
            return(new_cits)
        else:
            return([])

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
            description = self.description(tool)
            publication = self.publication(tool)
            test = tool.get('test', False)
            input = self.data_formats(tool, 'inputs')
            output = self.data_formats(tool, 'outputs')
            documentation = self.documentation(tool)
            citation = self.citation(tool)
            download = [tool.get('@source_url')]
            operating_system = ['Linux', 'macOS']
            source = ['toolshed']
        

            new_instance = instance(
                name = name,
                type = type_,
                version = version,
                source = source,
                download = download,
                label = label,
                description = description,
                publication = publication,
                documentation = documentation,
                operating_system = operating_system,
                test = test,
                input = input,
                output = output,
                citation = citation
                )
                
            
            standardized_tools.append(new_instance)
            return standardized_tools

        else:
            return standardized_tools
    
    
    