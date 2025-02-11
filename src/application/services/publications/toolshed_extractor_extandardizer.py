from typing import Dict, Any, List
from src.application.services.publications.publication_standardizer import PublicationStandardizer
from src.application.services.publications.publication_extractor import PublicationExtractor

class ToolshedPublicationExtractor(PublicationExtractor):
    """Extracts publication data from Galaxy Toolshed."""

    def extract_publications(self) -> List[Dict]:
        if self.raw_data['data'].get('publication'):
            return self.raw_data['data'].get('publication')
        else:
            return []

class ToolshedPublicationStandardizer(PublicationStandardizer):
    """Standardizes publication data from Galaxy Toolshed."""

    def standardize(self) -> Dict[str, Any]:
        try:
            # TODO: Implement the standardization logic here
            metadata = {
                "doi": '',
                "url": '',
                "pmid": '',
                "pmcid": '',
                "title": '',
                "authors": '',
                "published_year": '',
                "journal": '',
                "citations": {}
            }

            return metadata

        except Exception as e:
            self.log_error(f"Error processing Galaxy Toolshed publication data: {str(e)}")
            return {}