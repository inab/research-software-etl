import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("rs-etl-pipeline")


class MetadataStandardizer(ABC):
    def __init__(self, source):
        self.source = source
        logger.debug('Generator for ' + self.source + ' initialized') 

    @classmethod
    def process_transformation(self, tool):
        """Template method that defines the algorithm steps."""
        standardized_tools = []
        try:
            standardized_tools = self.transform_one(tool, standardized_tools)
        except Exception as e:
            logger.error('while transforming tool: ' + str(e))
            raise
            #raise Exception('while transforming tool: ' + str(e))
        return standardized_tools

    @classmethod
    def transform_one(self, tool, standardized_tools):
        '''
        Transforms one tool into an instance.
        '''
        pass

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
            name = fields[6].split(':')[1]
            if len(fields[6].split(':'))>2:
                version = fields[6].split(':')[2]
                source = fields[6].split(':')[0]
            else:
                version = None
                source = fields[5].split(':')[0]
            type_ = fields[7]
        
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
    
    """
    TODO: move to infrastructure layer

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
    """
        