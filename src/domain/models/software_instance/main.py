from pydantic import BaseModel, field_validator, HttpUrl, AnyUrl,  Field
from typing import List, Optional, Dict
from enum import Enum
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
    languages: List[str] = Field([],
                                title="Languages",
                                description="List of programming languages of the software.",
                                example=["R", "Rebol"])
    citation: Optional[List[dict]] = Field([],
                                title="Citation",
                                description="How to cite the software.")
    
            
    class Config:
        extra = "allow"
        # Serialize Enums to their string values
        json_encoders = {
            software_types: lambda v: v.value,
            operating_systems: lambda v: v.value,
            data_sources: lambda v: v.value
            }

    def merge(self, other: 'instance') -> 'instance':
        '''
        Merges two instances of the same software into one.
        The name and the type must be the same.
        In lists, the duplication of items is avoided.
        '''
        if self.name != other.name:
            raise ValueError("The names of the instances must be the same.")
        if self.type != other.type:
            raise ValueError("The types of the instances must be the same.")
        
        self.version = list(set(self.version + other.version))
        self.label = list(set(self.label + other.label))
        self.links = list(set(self.links + other.links))
        self.webpage = list(set(self.webpage + other.webpage)) ## 
        self.download = list(set(self.download + other.download))
        self.repository = self.merge_repositories(other.repository)
        self.operating_system = list(set(self.operating_system + other.operating_system))
        self.source_code = list(set(self.source_code + other.source_code))
        self.https = self.https or other.https # True if any of the instances has it
        self.ssl = self.ssl or other.ssl # True if any of the instances has it
        self.operational = self.operational or other.operational # True if any of the instances has it
        self.bioschemas = self.bioschemas or other.bioschemas # True if any of the instances has it
        self.source = list(set(self.source + other.source)) 
        # ------- from here, tests are needed -------
        self.edam_topics = list(set(self.edam_topics + other.edam_topics))
        self.edam_operations = list(set(self.edam_operations + other.edam_operations))
        self.description = list(set(self.description + other.description))
        self.test = self.test or other.test # True if any of the instances has it
        self.inst_instr = self.inst_instr or other.inst_instr # True if any of the instances has it
        self.dependencies = list(set(self.dependencies + other.dependencies))
        self.contribution_policy = self.contribution_policy or other.contribution_policy # True if any of the instances has it
        self.tags = list(set(self.tags + other.tags))

        # Has tests
        self.input = self.merge_data_formats(self.input, other.input)
        self.output = self.merge_data_formats(self.output, other.output)
        self.documentation = self.merge_documentation(other.documentation)
        self.license = self.merge_licenses(other.license)
        self.termsUse = self.termsUse or other.termsUse # True if any of the instances has it
        self.authors = self.merge_authors(other.authors)
        self.publication = self.merge_publications(other.publication)
        self.languages = list(set(self.languages + other.languages))
        self.citation = self.merge_citations(other.citation)
        self.topics = self.merge_topics(other.topics)
        self.operations = self.merge_operations(other.operations)

        return self


            
    def merge_repositories(self, other_repository):
        """
        Merges the other_repository into the self_repository by appending repositories that don't already exist.

        Args:
            self_repository (list): The list of repositories to merge into.
            other_repository (list): The list of repositories to merge from.

        Returns:
            list: The merged list of repositories.
        """
        existing_urls = [repo.url for repo in self.repository] 
        resulting_repositories = self.repository
        for repo in other_repository:
            if repo.url not in existing_urls:
                resulting_repositories.append(repo)

        return resulting_repositories

    def merge_data_formats(self, formats1, formats2):
        merged_formats = []

        # Create a dictionary to track merged formats by their unique keys (vocabulary + term)
        format_map = {}

        for fmt in formats1 + formats2:
            key = (fmt.vocabulary, fmt.term)
            if key in format_map:
                # Merge with the existing entry
                format_map[key] = format_map[key].merge(fmt)
            else:
                # Add new entry
                format_map[key] = fmt

        # Convert the dictionary back to a list
        merged_formats = list(format_map.values())
        return merged_formats
    
    def merge_documentation(self, other_documentation: list) -> None:
        """
        Merges the documentation list from another instance into this instance.
        Ensures that no duplicate documentation items are added and that the most complete
        information is retained.
        """
        # Dictionary to track documentation by (type, url) keys
        doc_map = {(doc.type, doc.url): doc for doc in self.documentation}

        for doc in other_documentation:
            key = (doc.type, doc.url)
            if key in doc_map:
                # Merge the existing documentation item with the new one
                doc_map[key] = doc_map[key].merge(doc)
            else:
                # Add the new documentation item if not already present
                doc_map[key] = doc

        documentation = list(doc_map.values())

        return documentation
    

    def merge_licenses(self, other_licenses: list) -> None:
        """
        Merges the licenses list from another instance into this instance.
        Ensures that no duplicate licenses are added and that the most complete
        information is retained.
        """
        # Dictionary to track licenses by their name
        license_map = {lic.name: lic for lic in self.license}

        for lic in other_licenses:
            if lic.name in license_map:
                # Merge with the existing license item
                license_map[lic.name] = license_map[lic.name].merge(lic)
            else:
                # Add the new license item if not already present
                license_map[lic.name] = lic

        resulting_licenses = list(license_map.values())

        return resulting_licenses
    
    def merge_authors(self, other_authors: list) -> None:
        """
        Merges the authors list from another instance into this instance.
        Ensures that no duplicate authors are added and that the most complete
        information is retained.
        """
        # Dictionary to track contributors by their name
        author_map = {author.name: author for author in self.authors}

        for author in other_authors:
            if author.name in author_map:
                # Merge with the existing contributor item
                author_map[author.name] = author_map[author.name].merge(author)
            else:
                # Add the new contributor item if not already present
                author_map[author.name] = author

        resulting_authors = list(author_map.values())

        return resulting_authors
    
    def merge_publications(self, other_publications: list) -> None:
        """
        Merges the publications list from another instance into this instance.
        Ensures that no duplicate publications are added and that the most complete
        information is retained.
        """
        # Dictionary to track publications by DOI, PMCID, or PMID
        publication_map = {pub.doi or pub.pmcid or pub.pmid or pub.title: pub for pub in self.publication}

        for pub in other_publications:
            key = pub.doi or pub.pmcid or pub.pmid or pub.title
            if key in publication_map:
                # Merge with the existing publication item
                publication_map[key] = publication_map[key].merge(pub)
            else:
                # Add the new publication item if not already present
                publication_map[key] = pub

        resulting_publications = list(publication_map.values())
        return resulting_publications
    
    def merge_citations(self, other_citations: List[Dict]) -> None:
        """
        Merges the citations list from another SoftwareInstance into this instance.
        Ensures that no duplicate citations are added and that the most complete
        information is retained.
        """
        citation_map = {}

        for citation in self.citation + other_citations:
            # Generate a unique key based on essential fields
            key = (citation.get('title', ''), citation.get('year', ''), citation.get('DOI', ''))

            if key in citation_map:
                # Merge the existing citation with the new one
                citation_map[key] = self._merge_two_citations(citation_map[key], citation)
            else:
                # Add the new citation if not already present
                citation_map[key] = citation

        # Update the citations list with the merged results
        self.citation = list(citation_map.values())

        # Remove any citations that are fully contained within another
        resulting_citation = [cit for i, cit in enumerate(self.citation) 
                        if not any(self._is_subset(cit, other) for j, other in enumerate(self.citation) if i != j)]
        
        return resulting_citation

    def _is_subset(self, cit1: Dict, cit2: Dict) -> bool:
        """
        Check if cit1 is a subset of cit2, meaning all non-empty fields in cit1
        are present and equal in cit2.
        """
        return all(cit2.get(key) == value for key, value in cit1.items() if value)

    def _merge_two_citations(self, cit1: Dict, cit2: Dict) -> Dict:
        """
        Merges two citation dictionaries, preferring non-empty and more complete fields.
        If one citation is more complete than the other, it will replace the less complete one.
        """
        merged_citation = {}

        # Merge fields, preferring the non-empty or more complete value
        for key in set(cit1.keys()).union(cit2.keys()):
            value1 = cit1.get(key)
            value2 = cit2.get(key)
            
            if isinstance(value1, list) and isinstance(value2, list):
                # Merge lists by combining and removing duplicates
                merged_citation[key] = list(set(value1 + value2))
            else:
                # Prefer the more complete value
                merged_citation[key] = value1 or value2

        return merged_citation
    
    def merge_operations(self, other_operations: list) -> None:
        """
        Merges the operations list from another instance into this instance.
        Ensures that no duplicate operations are added and that the most complete
        information is retained.
        """
        operation_map = {(op.uri, op.term): op for op in self.operations}

        for operation in other_operations:
            key = (operation.uri, operation.term)
            if key in operation_map:
                # Merge with the existing operation
                operation_map[key] = operation_map[key].merge(operation)
            else:
                # Add the new operation if not already present
                operation_map[key] = operation

        resulting_operations = list(operation_map.values())
        return resulting_operations

    def merge_topics(self, other_topics: list) -> None:
        """
        Merges the topics list from another instance into this instance.
        Ensures that no duplicate topics are added and that the most complete
        information is retained.
        """
        topic_map = {(tp.uri, tp.term): tp for tp in self.topics}

        for topic in other_topics:
            key = (topic.uri, topic.term)
            if key in topic_map:
                # Merge with the existing topic
                topic_map[key] = topic_map[key].merge(topic)
            else:
                # Add the new topic if not already present
                topic_map[key] = topic

        resulting_topics = list(topic_map.values())
        return resulting_topics


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