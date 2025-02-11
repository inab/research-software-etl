from typing import Dict, Any, List
from src.application.services.publications.publication_standardizer import PublicationStandardizer
from src.application.services.publications.publication_extractor import PublicationExtractor
from src.domain.models.software_instance.publication import Publication
from src.shared.utils import validate_and_filter

class BiotoolsPublicationExtractor(PublicationExtractor):
    """Extracts publication data from Biotools."""

    def extract_publications(self) -> List[Dict]:
        '''
        THe puclications are in the 'publications' (data.publications) field of the raw data.
        '''
        if self.raw_data['data'].get('publications'):
            return self.raw_data['data'].get('publications')
        else:
            return []

class BiotoolsPublicationStandardizer(PublicationStandardizer):
    """Standardizes publication data from Biotools."""

    def standardize(self) -> Dict[str, Any]:
        '''
        bio.tools entries only have the following information (usually only one):
        - doi
        - pmid
        - pmcid
        '''
        try:
            publication_meta_dict = {
                "doi": self.raw_data.get("doi", None),
                "pmid": self.raw_data.get("pmid", None),
                "pmcid": self.raw_data.get("pmcid", None),
            }

            new_publication = validate_and_filter(Publication, **publication_meta_dict)

            return new_publication


            return 

        except Exception as e:
            self.log_error(f"Error processing Biotools publication data: {str(e)}")
            return {}