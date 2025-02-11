from typing import Dict, Any, List
from src.application.services.publications.publication_standardizer import PublicationStandardizer
from src.application.services.publications.publication_extractor import PublicationExtractor
from src.domain.models.software_instance.publication import Publication
from src.shared.utils import validate_and_filter

class BiotoolsPublicationExtractor(PublicationExtractor):
    """Extracts publication data from Biotools."""

    @classmethod
    def extract_publications(cls, raw_data) -> List[Dict]:
        '''
        THe puclications are in the 'publications' (data.publications) field of the raw data.
        '''
        if raw_data['data'].get('publications'):
            return raw_data['data'].get('publications')
        else:
            return []

class BiotoolsPublicationStandardizer(PublicationStandardizer):
    """Standardizes publication data from Biotools."""

    @classmethod
    def standardize(cls, raw_data) -> Dict[str, Any]:
        '''
        bio.tools entries only have the following information (usually only one):
        - doi
        - pmid
        - pmcid
        '''
        try:
            publication_dict = {
                "doi": raw_data.get("doi", None),
                "pmid": raw_data.get("pmid", None),
                "pmcid": raw_data.get("pmcid", None),
            }

            publication = validate_and_filter(Publication, **publication_dict)

            return publication

        except Exception as e:
            cls.log_error(f"Error processing Biotools publication data: {str(e)}")
            return {}