from typing import Dict, Any, List
from src.application.services.publications.publication_standardizer import PublicationStandardizer
from src.application.services.publications.publication_extractor import PublicationExtractor
from src.domain.models.publication.publication import Publication
from src.shared.utils import validate_and_filter
import re
import logging

logger = logging.getLogger("rs-etl-pipeline")

class BiocondaRecipesPublicationExtractor(PublicationExtractor):
    """Extracts publication data from Bioconda recipes."""

    @classmethod
    def extract_publications(cls, raw_data) -> List[Dict]:
        new_pubids = set()
        # Extract DOIs
        if raw_data.get('data'):
            if raw_data['data'].get('extra'):
                if raw_data['data']['extra'].get('identifiers'):
                    for identifier in raw_data['data']['extra'].get('identifiers'):
                        reg1 = 'https:\/\/doi.org\/(10.([\w.]+?)\/([\w.]+)([\w.\/]+)?)'
                        reg2 = 'doi:(10.([\w.]+?)\/([\w.]+)([\w.\/]+)?)'
                        m1 = re.match(reg1, identifier)
                        m2 = re.match(reg2, identifier)
                        if m1:
                            new_pubids.add(m1.group(1))
                        if m2:
                            new_pubids.add(m2.group(1))

                if raw_data['data']['extra'].get('doi'):
                    for doi in raw_data['data']['extra'].get('doi'):
                        if doi != 'NA':
                            new_pubids.add(doi)
        
        # Build the publications dictionary
        publications = []        
        for pubid in new_pubids:
            publications.append({
                'doi': pubid
            })
    
        return publications

class BiocondaRecipesPublicationStandardizer(PublicationStandardizer):
    """Standardizes publication data from Bioconda recipes."""

    @classmethod
    def standardize(cls, raw_data) -> Dict[str, Any]:
        try:
            
            publication_dict = {
                "doi": raw_data.get("doi"),
                "title": None
            }

            publication = validate_and_filter(Publication, **publication_dict)

            return publication

        except Exception as e:
            logger.error(f"Error processing Bioconda recipes publication data: {str(e)}")
            return {}