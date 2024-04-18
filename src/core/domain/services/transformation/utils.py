import logging
import requests
from abc import ABC, abstractmethod
import src.core.shared.utils

class MetadataStandardizer(ABC):
    def __init__(self, source, ignore_empty_bioconda_types=False):
        self.source = source
        self.bioconda_types = self.generate_bioconda_types()
        self.ignore_empty_bioconda_types = ignore_empty_bioconda_types
        logging.debug('Generator for ' + self.source + ' initialized') 
    
    def process_transformation(self, tool):
        """Template method that defines the algorithm steps."""
        standardized_tools = []
        try:
            self.transform_one(standardized_tools, tool)
        except Exception as e:
            logging.error('while transforming tool: ' + str(e))
            raise Exception('while transforming tool: ' + str(e))
        return standardized_tools

    @abstractmethod
    def transform_one(self, tool, standardized_tools):
        '''
        Transforms one tool into an instance.
        '''
        pass

    def check_bioconda_types_empty(self):
        """Checks if bioconda_types is empty. If it is, it raises an exception."""
        if self.ignore_empty_bioconda_types == False:
            if self.bioconda_types == {}:
                logging.error('bioconda_types is empty, aborting transformation')
                raise Exception('bioconda_types is empty, aborting transformation')


    @staticmethod
    def generate_bioconda_types():
        '''
        This function returns a dictionary with the types of the bioconda tools in the pretools collection.
        '''
        bioconda_types = {}
        try:
            pretools = src.core.shared.utils.connect_collection(collection='pretools')
            biocondaCursor = pretools.find({'source': 'bioconda'}, {'name': 1, 'type': 1, '_id': 0})
        except:
            logging.error('while generating bioconda_types: could not connect to the pretools collection')
        else:
            for tool in biocondaCursor:
                bioconda_types[tool['name']] = tool['type']
    
        return(bioconda_types)


    @staticmethod
    def clean_name(name):
        '''
        if isinstance(name, str):
            bioconductor=re.search("^bioconductor-", name)
            if bioconductor:
                name=name[bioconductor.end():]
            emboss_dots=re.search("^emboss: ", name)
            if emboss_dots:
                name=name[emboss_dots.end():]
            emboss_unders=re.search("^emboss__", name)
            if emboss_unders:
                name=name[emboss_unders.end():]
        else:
            logging.warning('name is not a string')
        '''
        # In order to be able to relate dependencies, etc, we keep the name as it is

        return(name)
        
    @staticmethod
    def extract_ids(id_):
    # Extract ids from metrics @id
        fields = id_.split('/')
        if len(fields)>6:
            name = fields[5].split(':')[1]
            if len(fields[5].split(':'))>2:
                version = fields[5].split(':')[2]
                source = fields[5].split(':')[0]
            else:
                version = None
                source = fields[5].split(':')[0]
            type_ = fields[6]
        
            ids = {
                'name' : name,
                'version' : version,
                'type' : type_,
                'source': source
            }

            return(ids)
        
        return(False)
    
    @staticmethod
    def get_repo_name_version_type(id_):
        fields = id_.split('/')
        name_plus = fields[5]
        name_plus_fields=name_plus.split(':')
        name=name_plus_fields[1]
        if len(name_plus_fields)>2:
            version=name_plus.split(':')[2]
        else:
            version=None 

        if len(fields)>6:
            type_=fields[6]
        else:
            type_=None
        
        return({'name':name, 'version':version, 'type':type_})
    
    @staticmethod
    def page_exists(url):
        '''
        Checks if the url exists.
        - url: url to check
        '''
        try:
            r = requests.head(url)
            return r.status_code == 200
        except:
            return False

        