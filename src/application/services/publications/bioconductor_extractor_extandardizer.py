from typing import Dict, Any, List
from src.application.services.publications.publication_standardizer import PublicationStandardizer
from src.application.services.publications.publication_extractor import PublicationExtractor
from src.domain.models.software_instance.publication import Publication
from src.shared.utils import validate_and_filter


class BioconductorPublicationExtractor(PublicationExtractor):
    """Extracts publication data from Bioconductor."""

    def extract_publications(self) -> List[Dict]:
        if self.raw_data['data'].get('publication'):
            return self.raw_data['data'].get('publication')
        else:
            return []

class BioconductorPublicationStandardizer(PublicationStandardizer):
    """Standardizes publication data from Bioconductor."""

    def standardize(self) -> Dict[str, Any]:
        try:
            
            publication_dict = {
                "doi": self.raw_data.get("doi"),
                "url": self.raw_data.get("url"),
                "pmid": self.raw_data.get("pmid"),
                "pmcid": self.raw_data.get("pmcid"),
                "title": self.raw_data.get("title"),
                "authors": self.raw_data.get("authors"),
                "published_year": self.raw_data.get("published_year"),
                "journal": self.raw_data.get("journal"),
                "citations": {}
            }

            new_publication = validate_and_filter(Publication, **publication_dict)

            return new_publication

        except Exception as e:
            self.log_error(f"Error processing Bioconductor publication data: {str(e)}")
            return {}