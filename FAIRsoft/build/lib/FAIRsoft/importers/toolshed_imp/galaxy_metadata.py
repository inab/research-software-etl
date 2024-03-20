import os
import FAIRsoft
class dMetadataFetcher():
    def __init__(self, tools_galaxy_metadata):
        self.repositories = tools_galaxy_metadata
        self.seen_tools = set()
        
    def get_dependencies(self, latest_revision):
        if latest_revision['tool_dependencies']:
            return(list(latest_revision['tool_dependencies'].keys()))
        else:
            return([])
    
    def retrieve_metadata(self, tool):
        if tool:
            latest_revision_id = max(iter(tool.keys()))
            latest_revision = tool[latest_revision_id]
            if 'tools' in latest_revision.keys():
                dependencies = self.get_dependencies(latest_revision)
                for t in latest_revision['tools']:
                    if latest_revision['tools'][0]['id']+latest_revision['tools'][0]['version'] not in self.seen_tools:
                        entry = {}
                        entry['id'] = latest_revision['tools'][0]['id']
                        entry['name'] = latest_revision['tools'][0]['name']
                        entry['version'] = latest_revision['tools'][0]['version']
                        entry['dependencies'] = dependencies
                        entry['@data_source'] = "galaxy_metadata"
                        self.seen_tools.add(latest_revision['tools'][0]['id']+latest_revision['tools'][0]['version'])
                        entry['@id'] = 'https://openebench.bsc.es/monitor/tool/galaxy_metadata:{name}:{version}/cmd'.format(name=entry['id'], version=entry['version'])
                        return(entry)
        return({})

    def process_metadata(self):
        STORAGE_MODE = os.getenv('STORAGE_MODE', 'db')
        ALAMBIQUE = os.getenv('ALAMBIQUE', 'alambique')

        if STORAGE_MODE =='db':
            alambique = FAIRsoft.utils.connect_collection(ALAMBIQUE)
        else:
            OUTPUT_PATH = os.getenv('OUTPUT_PATH', './')
            OUTPUT_TOOLSHED=os.getenv('OUTPUT_TOOLSHED', 'toolshed.json')
            output_file = OUTPUT_PATH + '/' + ALAMBIQUE + '/' + OUTPUT_TOOLSHED

        log = {'names':[],
                'n_ok':0,
                'errors': []}

        for tool in self.repositories:
            entry = self.retrieve_metadata(tool)
            if entry:
                if STORAGE_MODE=='db':
                    log = FAIRsoft.utils.push_entry(entry, alambique, log)
                else:
                    log = FAIRsoft.utils.save_entry(entry, output_file, log)
            else:
                continue

