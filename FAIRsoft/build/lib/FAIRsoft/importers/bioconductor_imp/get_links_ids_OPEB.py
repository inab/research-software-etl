import re
import os

url_id_bioc = {}
links = set()

def clean_url(url):
    URL_BIOCONDUCTOR=os.getenv('URL_BIOCONDUCTOR', 'https://bioconductor.org/packages/.*/bioc/.*')
    if re.search(URL_BIOCONDUCTOR, url):
        print(url)


def get_all_ids_links(tools):
    for tool in tools:
        if 'bioconductor' in tool['homepage']:
            url_id_bioc[tool['homepage']] = tool['@id']
    return(url_id_bioc)



