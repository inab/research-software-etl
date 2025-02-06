'''
This file uses the PublicationMetadataRepository.

# Initialization:
mongo_adapter = MongoDBAdapter()
publications_repo = PublicationsMetadataRepository(mongo_adapter)

# Usage: 
print(publications_repo.entry_exists("some_id"))
publications_repo.save_entry({"_id": "456", "title": "Some Publication"})

'''

import os
from typing import Dict, Any, Optional, List
from src.infrastructure.db.mongo_adapter import MongoDBAdapter
from src.adapters.db.publications_repository import PublicationsMetadataRepository
from infrastructure.db.database_adapter import DatabaseAdapter
from src.application.services.publications.publication_standardizer_factory import StandardizerFactory


PUBLICATIONS_COLLECTION = os.getenv('PUBLICATIONS_COLLECTION', 'publicationsDev')

def publication_in_collection(publication: Dict[str, Any], publications_repo: DatabaseAdapter) -> Optional[str]:
    '''
    Checks if the publication is already in the publications collection.
    - publication: publication to be checked
    - db_adapter: database adapter
    '''
    # Check doi
    if publication.get('doi'):
        entry = publications_repo.find_by_doi(publication.get('doi'))
        if entry:
            return entry['_id']

    # Check title 
    elif publication.get('title'):
        entry = publications_repo.find_by_title(publication.get('title'))
        if entry:
            return entry['_id']

    # Check URL 
    elif publication.get('url'):
        entry = publications_repo.find_by_url(publication.get('url'))
        if entry:
            return entry['_id']

    # Check pmid 
    elif publication.get('pmid'):
        entry = publications_repo.find_by_pmid(publication.get('pmid'))
        if entry:
            return entry['_id']

    # Check pmcid
    elif publication.get('pmcid'):
        entry = publications_repo.find_by_pmcid(publication.get('pmcid'))
        if entry:
            return entry['_id']

    return None


def add_publication(publication: Dict[str, Any], publications_repo: DatabaseAdapter) -> str:
    '''
    Add a publication to the publications collection.
    - publication: publication to be added
    - db_adapter: database adapter
    '''
    # Generate entry metadata
    metadata_dict = publications_repo.create_new_metadata(publication)

    # Build entry to insert in database 
    metadata_dict['data'] = publication 

    # Insert in database
    publications_repo.save_entry(metadata_dict)
    return


def extract_publications(source_name : str, publications : List[Dict[str, Any]]) -> List[str]:

    mongo_adapter = MongoDBAdapter()
    publications_repo = PublicationsMetadataRepository(mongo_adapter)
    
    publications_ids = set()
    if len(publications) > 0:
        for publication in publications:

            # Parse the entry 
            publication_standardizer = StandardizerFactory.get_standardizer(source_name, publication)
            standardized_publication = publication_standardizer.standardize()
            
            # Check if the publication is already in the publications collection
            publication_id = publication_in_collection(standardized_publication, publications_repo)
            if publication_id:
                publications_ids.add(publication_id)
            else:
                publication_id = add_publication(standardized_publication, publications_repo)
                publications_ids.add(publication_id)
        
    return list(publications_ids)

                
        