"""
This is the instance model used for standardizing the metadata of software instances. 

The "data" in entries in the pretools collection follow the schema defined in this model.

The "data" in entries in the tools collection (post integration) follow a modified version of this schema (multitype_instance.py).
"""

from pydantic import BaseModel, field_validator, HttpUrl, AnyUrl,  Field
from pydantic_core.core_schema import ValidationInfo
from typing import List, Optional, Any
from enum import Enum
from bson import ObjectId
import re
import logging

from src.domain.models.software_instance.data_format import data_format
from src.domain.models.software_instance.documentation import documentation_item
from src.domain.models.software_instance.license import license_item
from src.domain.models.software_instance.recognition import contributor
from src.domain.models.software_instance.topic_operation import vocabulary_topic, vocabulary_operation
from src.domain.models.software_instance.repository import repository_item

class setOfInstances(object):

    def __init__(self, source):
        self.source = source
        self.instances = []

class software_types(str, Enum):
    cmd = 'cmd'
    web = 'web'
    db = 'db'
    app = 'app'
    lib = 'lib'
    ontology = 'ontology'
    workflow = 'workflow'
    plugin = 'plugin'
    sparql = 'sparql'
    soap = 'soap'
    script = 'script'
    rest = 'rest'
    workbench = 'workbench'
    suite = 'suite'
    undefined = 'undefined'

class operating_systems(str, Enum):
    Linux = 'Linux'
    Windows = 'Windows'
    macOS = 'macOS'
    BSD = 'BSD'
    Solaris = 'Solaris'
    Android = 'Android'
    iOS = 'iOS'
    ChromeOS = 'ChromeOS'
    other = 'other'


class data_sources(str, Enum):
    bioconda = "bioconda"
    bioconda_recipes = "bioconda_recipes"
    bioconductor = "bioconductor"
    biotools = "biotools"
    bitbucket = "bitbucket"
    galaxy = "galaxy"
    galaxy_metadata = "galaxy_metadata"
    github = "github"
    opeb_metrics = "opeb_metrics"
    sourceforge = "sourceforge"
    toolshed = "toolshed"



class instance(BaseModel, validate_assignment=True):
    '''
    Class to represent a FAIRsoft instance.
    '''
    name : str = Field(..., 
                       title="Name", 
                       description="Name of the software. This is the equivalent of an identifier of the tool.", 
                       example="trimal")
    type : Optional[software_types] = Field(None, 
                                            title="Type of software", 
                                            description="""The type of software can be: cmd, web, db, app, 
                                            lib, ontology, workflow, plugin, sparql, soap, script, rest, 
                                            workbench, suite""",
                                            example="cmd")
    version: List[str] = Field([],
                               title="Version",
                               description="""List of versions of the software. The version of a software 
                               indicates its specific state of development and release, typically represented 
                               by numbers and sometimes letters, to denote upgrades, bug fixes, and new 
                               features since its initial or previous release.""",
                               example=["1.4.0", "1.4.2"])
    label : List[str] = Field([],
                              title="Label(s)",
                              description="""List of full names of the software. These are displayed as the name 
                              of the software in UIs. The elements of the lists are most of the time variations of
                              each other""",
                              example=['TrimAl', 'Trimal'])
    links : List[AnyUrl] = []
    webpage : List[HttpUrl] = Field([],
                                    title="Webpage",
                                    description="""List of webpages of the software. Ideally the homepage should 
                                    be included here.""")
    download : List[AnyUrl] = Field([],
                                    title="Download links",
                                    description="Download of executables or soure code of the software.",
                                    example=["https://bioconductor.org/packages/3.16/bioc/src/contrib/simpleSeg_1.0.0.tar.gz"]
                                    )
    repository : List[repository_item] = Field([], 
                                               title="Repository",
                                               description="""Location from which the software can be retrieved and 
                                               installed on a computer. They are often the place for centralized 
                                               development.""",
                                               example=["https://github.com/inab/trimal"])
    operating_system : List[operating_systems] = Field([],
                                                        title="Operating system",
                                                        description="""List of operating systems on which the software 
                                                        can be installed and run. The operating system is the software 
                                                        that supports a computer's basic functions, such as scheduling 
                                                        tasks, executing applications, and controlling peripherals.""",
                                                        example=["Linux", "macOS"])
    source_code : List[AnyUrl] = Field([],
                                        title="Source code",
                                        description="""List of source code links of the software. The source code 
                                        is the version of software as it is originally written (i.e., typed into a 
                                        computer) by a human in plain text (i.e., human readable alphanumeric 
                                        characters).""",
                                        example=["https://bioconductor.org/packages/3.16/bioc/src/contrib/simpleSeg_1.0.0.tar.gz"]
                                        )
    https : bool = Field(False,
                            title="HTTPS",
                            description="Indicates whether the webpage of the software uses the HTTPS protocol.",
                            example=True)
    ssl : bool = Field(False,
                        title="SSL",
                        description="Indicates whether the webpage of the software uses the SSL protocol.",
                        example=True)
    operational : bool = Field(False,
                                title="Operational",
                                description="Indicates whether the webpage of the software is operational.",
                                example=True)
    bioschemas : bool = Field(False,
                                title="Bioschemas",
                                description="Indicates whether the webpage of the software uses Bioschemas.",
                                example=True)
    source : List[data_sources] = Field([],
                                        title="Source",
                                        description="List of sources of the software metadata contained in this object.",
                                        example=["bioconductor"])
    edam_topics : List[HttpUrl] = Field([],
                                        title="EDAM topics",
                                        description="List of EDAM topics of the software.",
                                        example=["http://edamontology.org/topic_0091"])
    edam_operations : List[HttpUrl] = Field([],
                                             title="EDAM operations",
                                             description="List of EDAM operations of the software.",
                                             example=["http://edamontology.org/operation_0004"])

    description : List[str] = Field([],
                                    title="Description",
                                    description="""List of descriptions of the software. A description is a 
                                    detailed explanation of the software.""",
                                    example=["TrimAl is a tool for automated alignment trimming in large-scale phylogenetic analyses."]
                                    )
    test : bool = Field(False,
                        title="Test",
                        description="Indicates whether the software has test data.",
                        example=True) # WARNING: this is a list of links in Observatory API --> incompatibility
    inst_instr : bool = Field(False,
                                title="Installation instructions",
                                description="Indicates whether the software has installation instructions.",
                                example=True)
    dependencies : List[str] = Field([],
                                    title="Dependencies",
                                    description="List of dependencies of the software.",
                                    example=["R (>= 4.0)"])
    contribution_policy : bool = Field(False,
                                        title="Contribution policy",
                                        description="Indicates whether the software has a contribution policy.",
                                        example=True)
    tags : List[str] = Field([],
                            title="Tags",
                            description="List of tags of the software.",
                            example=["ELIXIR-ES"])
    input : List[data_format] = Field([],
                                    title="Input",
                                    description="List of input data formats of the software.")
    output : List[data_format] = Field([],
                                        title="Output",
                                        description="List of output data formats of the software.")
    documentation : List[documentation_item] = Field([],
                                                    title="Documentation",
                                                    description="List of documentation items of the software.")
    license : Optional[List[license_item]] = Field([],
                                                    title="License",
                                                    description="List of licenses of the software.")
    termsUse : bool = Field(False,
                            title="Terms of use",
                            description="Indicates whether the software has terms of use.",
                            example=True)
    authors : List[contributor] = Field([],
                                        title="Authors",
                                        description="List of authors of the software.")
    topics: List[vocabulary_topic] = Field([],
                                            title="Topics",
                                            description="List of topics of the software.")
    operations: List[vocabulary_operation] = Field([],
                                                    title="Operations",
                                                    description="List of operations of the software.")
    sources_labels: dict = {}
    publication: List[ObjectId] = Field([], 
                                    title="Publication",
                                    description="List of DB Ids of the software.")
    languages: List[str] = Field([],
                                title="Languages",
                                description="List of programming languages of the software.",
                                example=["R", "Rebol"])
    citation: Optional[List[dict]] = Field([],
                                title="Citation",
                                description="How to cite the software.")
    
            
    class Config:
        extra = "allow"
        arbitrary_types_allowed = True
        # Serialize Enums to their string values
        json_encoders = {
            software_types: lambda v: v.value,
            operating_systems: lambda v: v.value,
            data_sources: lambda v: v.value,
            ObjectId: str
            }


    @field_validator('name')
    @classmethod
    def empty_name(cls, value) -> str:
        '''
        Raises an error if the name is empty.
        '''
        # logging.info(f"-- Validating name: {value}")
        value = value.strip()
        if value == "":
            raise ValueError("The name cannot be empty.")
        return value

    @field_validator('version', mode="before")
    @classmethod
    def convert_integer(cls, value) -> str:
        '''
        Converts the version number to string if it is an integer.
        '''
        # logging.info(f"-- Validating version: {value}")
        if isinstance(value, int):
            return [ str(value) ]
        elif isinstance(value, list):
            return [ str(x) for x in value ]
        else:
            return value       
        
    @field_validator('label', mode="before")
    @classmethod
    def convert_string_label(cls, value) -> List[str]:
        '''
        Converts the label to a list if it is a string.
        '''
        # logging.info(f"-- Validating label: {value}")
        if isinstance(value, str):
            return [value]
        else:
            return value
    

    @field_validator('links', mode="after")
    @classmethod
    def clean_links(cls, value) -> List[AnyUrl]:
        '''
        If an element in links is not a file, remove it from the list.
        '''
        # logging.info(f"-- Validating links: {value}")
        new_links = []
        for link in value:
            if link.path:
                x = re.search("^(.*)(\\.)(rar|bz2|tar|gz|zip|bz|json|txt|js|py|md)$", link.path)
                if x:
                    # keep item in the list
                    new_links.append(link)
        
        return new_links
    

    @field_validator('webpage', mode="before")
    @classmethod
    def clean_webpage(cls, value) -> List[str]:
        # Ensure value is a list (for cases where it might be passed as a single string)
        # logging.info(f"-- Validating webpage before: {value}")
        if not value:
            return []
        else:
            if isinstance(value, str):
                value = [value]
            
            # Remove empty strings and None values
            elif isinstance(value, list):
                webpage = set()
                for link in value:
                    if link:
                        webpage.add(link)
            
            # Filter out URLs starting with "ftp://ftp."
            webpage = [
                url for url in value if not str(url).startswith("ftp://ftp.")
            ]
            
            return webpage


    @field_validator('webpage',  mode="after")
    @classmethod
    def compose_webpage(cls, value) -> List[str]:
        '''
        Remove file urls from webpage attribute.
        '''
        # logging.info(f"-- Validating webpage after: {value}")
        webpage = []
        
        if value:
            for link in value:
                if link.path:
                    x = re.search("^(.*)(\\.)(rar|bz2|tar|gz|zip|bz|json|txt|js|py|md)$", link.path)
                    if not x:
                        # remove the item from the list
                        webpage.append(link)
            
    
        return webpage
        
    @field_validator('operating_system', mode="before")
    @classmethod
    def convert_mac(cls, value) -> List[str]:
        ''''
        Converts mac to macOS.
        '''
        # logging.info(f"-- Validating operating_system: {value}")
        for i in range(len(value)):
            if value[i] == 'Mac':
                value[i] = 'macOS'
        return value

    @field_validator('source_code', mode="after")
    @classmethod
    def remove_duplicates(cls, value) -> List[str]:
        '''
        Removes duplicates from the source code links.
        '''
        # logging.info(f"-- Validating source_code: {value}")
        return list(set(value))
    
    @field_validator('description', mode="after")
    @classmethod
    def capitalize_first_letter_and_add_dot(cls, value) -> List[str]:
        '''
        Capitalizes the first letter of the description and adds a dot at the end.
        '''
        # logging.info(f"-- Validating description: {value}")
        descriptions = set(value)
        new_descriptions = set()
        for desc in descriptions:
            if desc == "":
                continue
            desc=desc.strip()
            first_letter = desc[0].capitalize()
            desc = first_letter + desc[1:]
            if desc[-1] != '.':
                desc += '.'
            new_descriptions.add(desc)
                
        return list(new_descriptions)


    @field_validator('license', mode="before")
    @classmethod
    def remove_empty_name_and_url(cls, value) -> List[str]:
        '''
        Removes empty name and url from the license.
        '''
        # logging.info(f"-- Validating license: {value}")
        
        new_licenses = []
        if isinstance(value, List):
            for item in value:
                if item.get('name') and item.get('url'):
                    new_licenses.append(item)
        
        return value

    @field_validator('license', mode="after")
    @classmethod
    def split_license(cls, value) -> List[str]:
        '''
        Splits the license string.
        '''
        # logging.info(f"-- Validating license: {value}")
        if isinstance(value, List):
            for item in value:
                if isinstance(item, str):
                    if "|" in item:
                        value.remove(item)
                        value.extend(item.split("|"))
        return value