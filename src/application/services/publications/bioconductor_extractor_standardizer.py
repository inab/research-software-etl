from typing import Dict, Any, List
from src.application.services.publications.publication_standardizer import PublicationStandardizer
from src.application.services.publications.publication_extractor import PublicationExtractor
from src.domain.models.publication.publication import Publication
from src.shared.utils import validate_and_filter
import logging

logger = logging.getLogger("rs-etl-pipeline")

class BioconductorPublicationExtractor(PublicationExtractor):
    """Extracts publication data from Bioconductor."""

    @classmethod
    def extract_publications(cls, raw_data) -> List[Dict]:
        if raw_data['data'].get('publication'):
            return raw_data['data'].get('publication')
        else:
            return []

class BioconductorPublicationStandardizer(PublicationStandardizer):
    """Standardizes publication data from Bioconductor."""

    @classmethod
    def standardize(cls, raw_data) -> Dict[str, Any]:
        try:
            
            publication_dict = {
                "doi": raw_data.get("doi"),
                "url": raw_data.get("url"),
                "pmid": raw_data.get("pmid"),
                "pmcid": raw_data.get("pmcid"),
                "title": raw_data.get("title"),
                "year": raw_data.get("published_year"),
                "journal": raw_data.get("journal")
            }

            publication = validate_and_filter(Publication, **publication_dict)

            return publication

        except Exception as e:
            logger.error(f"Error processing Bioconductor publication data: {str(e)}")
            return None