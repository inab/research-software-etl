# To transform the data from the github metadata api (https://github.com/inab/github-metadata-api) to the domain model

from src.application.services.transformation.metadata_standardizers import MetadataStandardizer
from src.domain.models.software_instance.main import instance

from pydantic import TypeAdapter, HttpUrl
from typing import Dict, Any
import logging
import re

# --------------------------------------------
# GitHub Tools Transformer
# --------------------------------------------

class githubStandardizer(MetadataStandardizer):

    def __init__(self, source = 'github', ignore_empty_bioconda_types = True):
        MetadataStandardizer.__init__(self, source, ignore_empty_bioconda_types)

    @classmethod
    def repository(cls, tool: Dict[str, Any]):
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
    
    @classmethod
    def authors(cls, tool: Dict[str, Any]):
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


                
    def transform_one(self, tool, standardized_tools):
        '''
        Transforms one tool to the standardized format.
        '''
        
        data = tool['data']
        standardized_tool = instance(
            name = data['name'],
            source = ['github'],
            description = data['description'],
            type = None,
            version = data['version'],
            label = data['label'],
            links = data['links'],
            webpage = data['webpage'],
            download = data['download'],
            repository= self.repository(data),
            operating_system= data['os'],
            documentation= data['documentation'],
            authors= self.authors(data),
            publications= data['publication'],
            topics = data['topics']
        )
       

        standardized_tools.append(standardized_tool)