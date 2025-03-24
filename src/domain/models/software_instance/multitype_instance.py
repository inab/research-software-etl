"""
This is the instance model used for integrated metadata of software instances. 

The "data" in entries in the tools collection (post integration) this schema (multitype_instance.py).
"""

from src.domain.models.software_instance.main import instance, software_types
from typing import List, Dict

class multitype_instance(instance):
    '''
    Same as instance, but with a list of software types and other names.
    '''
    type : List[software_types]
    other_names : List[str]

    def merge(self, other: 'instance') -> 'instance':
        '''
        Merges two instances of the same software into one.
        In lists, the duplication of items is avoided.
        '''
        # Decide a name and put the other names in "other_names"
        # TODO: adjust naming logic after integration analysis (insights about naming)

        if self.name == other.name:
            self.other_names = list(set(self.other_names + other.other_names))
        else:
            self.other_names = list(set(self.other_names + [other.name] + other.other_names))
        
        self.type = list(set(self.type + other.type))
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
        self.publication = list(set(self.publication + other.publication))
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

