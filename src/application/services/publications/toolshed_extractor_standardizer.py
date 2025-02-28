import json
import bibtexparser
import logging
from typing import Dict, Any, List
from src.application.services.publications.publication_standardizer import PublicationStandardizer
from src.application.services.publications.publication_extractor import PublicationExtractor
from src.domain.models.publication.publication import Publication
from src.shared.utils import validate_and_filter

logger = logging.getLogger("rs-etl-pipeline")

class ToolshedPublicationExtractor(PublicationExtractor):
    """Extracts publication data from Galaxy Toolshed."""

    @staticmethod
    def parse_bibtex(ent):
        '''
        Gets journal publication information from bibtex citation.
        '''
        parser = bibtexparser.bparser.BibTexParser(common_strings=True)
        logger_bibtex = logging.getLogger('bibtexparser')
        new_entries = []
        try:
            bibtexdb = bibtexparser.loads(ent, parser=parser)
            for entry in bibtexdb.entries:
                if entry['ENTRYTYPE'].lower() != 'misc':
                    single_entry = {}
                    single_entry['url'] = entry.get('url')
                    single_entry['title'] = entry.get('title')
                    single_entry['year'] = entry.get('year')
                    single_entry['journal'] = entry.get('journal')
                    single_entry['doi'] = entry.get('doi')
                    single_entry['pmid'] = entry.get('pmid')
                    new_entries.append(single_entry)
        except Exception as err:
            logger.error(f'FAILED attempt to parse citation (bibtex). Error: {err}')
            logger.error(json.dumps(ent, sort_keys=False, indent=4))

        return(new_entries)
    
    @classmethod
    def extract_publications(cls, raw_data) -> List[Dict]:
        publications = []
        if raw_data['data'].get('citation'):
            for cit in raw_data['data']['citation']:

                if cit.get('type') == 'doi':
                    new_pub = {'doi':cit.get('citation')}
                    publications.append(new_pub)
                
                else:
                    new_entries = cls.parse_bibtex(cit.get('citation'))
                    for se in new_entries:
                        publications.append(se)
        
        return(publications)


class ToolshedPublicationStandardizer(PublicationStandardizer):
    """Standardizes publication data from Galaxy Toolshed."""

    @classmethod
    def standardize(cls, raw_data) -> Dict[str, Any]:
        try:
            publication_dict = {
                "doi": raw_data.get("doi"),
                "url": raw_data.get("url"),
                "title": raw_data.get("title"),
                "year": raw_data.get("year"),
                "journal": raw_data.get("journal"),
                "pmid": raw_data.get("pmid")
            }

            publication = validate_and_filter(Publication, **publication_dict)
            return publication

        except Exception as e:
            logger.error(f"Error processing Galaxy Toolshed publication data: {str(e)}")
            return {}