# To transform the data from the github metadata api (https://github.com/inab/github-metadata-api) to the domain model

from src.application.services.transformation.metadata_standardizers import MetadataStandardizer
from src.domain.models.software_instance.main import instance
from src.shared.utils import validate_and_filter

from typing import Dict, Any


# --------------------------------------------
# GitHub Tools Transformer
# --------------------------------------------

class githubStandardizer(MetadataStandardizer):

    def __init__(self, source = 'github'):
        MetadataStandardizer.__init__(self, source)

    @staticmethod
    def repository(tool: Dict[str, Any]):
        '''
        Returns the repository of the tool.
        '''
        if len(tool.get('repository')) > 0:
            return [{
                'url': tool.get('repository')[0],
                'kind': 'github'
            }]
        
        else:
            return []
    
    @staticmethod
    def authors(tool: Dict[str, Any]):
        '''
        Turns person into Person
        '''
        new_authors = []
        if tool.get('author'):
            for author in tool.get('author'):
                if author.get("type") == "person":
                    new_authors.append({
                        "name": author.get("name"),
                        "email": author.get("email"),
                        "type": "Person",
                        "maintainer": author.get("maintainer")
                    })
                else:
                    new_authors.append(author)

        return new_authors
    
    @staticmethod
    def webpage(tool: Dict[str, Any]):
        '''
        Returns the webpage of the tool.
        '''
        if tool.get('webpage') is None:
            return []
        
        webpage = []
        for item in tool.get('webpage'):
            if item:
                webpage.append(item)

        return webpage

    @classmethod
    def transform_one(cls, tool, standardized_tools):
        '''
        Transforms one tool to the standardized format.
        '''
        
        data = tool['data']

        new_instance_dict = {
            "name" : data['name'],
            "source" : ['github'],
            "description" : data['description'],
            "type" : None,
            "version" : data['version'],
            "label" : data['label'],
            "links" : data['links'],
            "webpage" : cls.webpage(data),
            "download" : data['download'],
            "repository" : cls.repository(data),
            "operating_system" : data['os'],
            "documentation" : data['documentation'],
            "authors" : cls.authors(data),
            "publications" : data['publication'],
            "topics" : data['topics']
        }
        
        # We keep only the fields that pass the validation
        new_instance = validate_and_filter(instance, **new_instance_dict)

        standardized_tools.append(new_instance)
       
        return standardized_tools