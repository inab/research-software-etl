import logging
from typing import Dict, Any, List
from src.application.services.publications.publication_standardizer import PublicationStandardizer
from src.application.services.publications.publication_extractor import PublicationExtractor
from src.domain.models.publication.publication import Publication
from src.shared.utils import validate_and_filter

logger = logging.getLogger("rs-etl-pipeline")


class OPEBMetricsPublicationExtractor(PublicationExtractor):
    """Extracts publication data from OPEB metrics."""

    @classmethod
    def extract_publications(cls, raw_data) -> List[Dict]:
        publications = []
        data = raw_data.get('data', {})
        if data.get('project'):
            if data['project'].get('publications'):
                for publication in data['project']['publications']:
                    publications.extend(publication.get('entries', []))        

        return publications

class OPEBMetricsPublicationStandardizer(PublicationStandardizer):
    """Standardizes publication data from OPEB metrics."""

    @classmethod
    def standardize(cls, raw_data) -> Dict[str, Any]:
        try:
            
            publication_dict = {
                "doi": raw_data.get("doi"),
                "pmid": raw_data.get("pmid"),
                "pmcid": raw_data.get("pmcid"),
                "title": raw_data.get("title"),
                "year": raw_data.get("year"),
                "url": raw_data.get("url"),
                "citations": [
                    {
                        "source_id": "europepmc",
                        "total_citations": raw_data.get("cit_count", None),
                        "citations_per_year" : raw_data.get("citations", []),
                        "last_updated": raw_data.get("last_updated", None)
                    }
                ]
            }

            publication = validate_and_filter(Publication, **publication_dict)

            return publication

        except Exception as e:
            logger.error(f"Error processing OPEB metrics publication data: {str(e)}")
            return {}