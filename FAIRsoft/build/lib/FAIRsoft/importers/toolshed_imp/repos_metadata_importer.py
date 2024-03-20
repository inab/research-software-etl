import requests
import json

session = requests.Session()

class reposFetcher():

    def __init__(self):
        self.tools = []

    def fetch_tools(self):
        repositories_list = self._get_repositories_dict()
        for repository_dict in repositories_list:
            if repository_dict['type']=='unrestricted':
                self.tools.append(galaxyTool(repository_dict))
        self.all_metadatas = [tool.metadata for tool in self.tools if tool.metadata]

    def _get_repositories_dict(self):
        REPS_URL = "https://toolshed.g2.bx.psu.edu/api/repositories?" 
        repositories_json = get_url(REPS_URL)
        repositories_dict_list =  json.loads(repositories_json.text) 
        return(repositories_dict_list)
    
    def export_metadatas(self, output_file_name):
        all_metadatas = [tool.metadata for tool in self.tools if tool.metadata]
        with open(output_file_name, 'w') as outputfile:
            json.dump(all_metadatas, outputfile)

class galaxyTool():
    def __init__(self, repository_dict):
        self.metadata =  self._get_metadata(repository_dict)
        self.revisions = self.metadata.keys()

    def _get_metadata(self, repository_dict):
        url_string = "https://toolshed.g2.bx.psu.edu/api/repositories/{id_}/metadata?"
        id_ = repository_dict['id']
        url = url_string.format(id_ = id_)
        req = get_url(url)
        meta = req.json()
        return(meta)

def get_url(url):
    try:
        re = session.get(url)
    except:
        print('Impossible to make the request')
        print("problematic url: " + url)
        return(None)
    else:    
        return(re)


if __name__ == '__main__':
    RF = reposFetcher()
    RF.fetch_tools()
    RF.export_metadatas('galaxy_metadatas.json')