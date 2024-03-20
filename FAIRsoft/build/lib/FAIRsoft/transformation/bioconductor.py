from FAIRsoft.utils import setOfInstances
from FAIRsoft.utils import instance
from FAIRsoft.transformation.meta_transformers import toolGenerator
from FAIRsoft.transformation.meta_transformers import clean_version
from FAIRsoft.transformation.meta_transformers import clean_name


class transformer(toolGenerator):
    def __init__(self, tools, source='bioconductor'):
        toolGenerator.__init__(self, tools, source)

        self.instSet = setOfInstances('bioconductor')

        for tool in self.tools:
            type_= 'lib'
            version = clean_version(tool['Version'])
            if version == None:
                version = 'unknown'
            name = clean_name(tool['name'])
            newInst = instance(name, type_, [version])
            newInst.description = [tool['description']] # string
            if tool['URL']:
                newInst.links = [tool['URL']]
            else:
                newInst.links = []
            
            newInst.publication = []
            if tool['publication'].get('url'):
                if tool['publication']['citation'].get('type') == 'article-journal':
                    journal = None
                    for a in tool['publication']['citation']['container-title']:
                        if 'ISSN' not in a:
                            journal = a
                    
                    fields = {}
                    for field in ['date', 'title']:
                        if tool['publication']['citation'].get(field):
                            fields[field] = tool['publication']['citation'][field][0]
                        else:
                            fields[field] = None
                    
                    if tool['publication'].get('url'):
                        url = tool['publication']['url'][0]
                    else:
                        url = None
                    
                    newInst.publication =  [{
                    'title': fields['title'],
                    'year': fields['date'],
                    'url': url,
                    'journal': journal,
                    }]

            
            download = []
            for a in ["Windows Binary", "Source Package", "Mac OS X 10 10.11 (El Capitan)"]:
                if a in tool.keys() and tool[a]:
                    download.append(tool['Package Short Url'] + tool[a])

            newInst.download = download
            newInst.inst_instr = tool['Installation instructions'] #
            newInst.src = [ a for a in newInst.download if a[0] == "Source Package"[0] ]# string
            newInst.os = ['Linux', 'Mac', 'Windows'] # list of strings
            if tool['Depends']:
                deps = tool['Depends']
            else:
                deps = []
            if tool['Imports']:
                impo = tool['Imports'].split(',')
            else:
                impo = []

            newInst.dependencies = [item for sublist in [deps+impo] for item in sublist] # list of strings

            newInst.documentation = [[ a, a[0] ] for a in tool['documentation']] # list of lists [[type, url], [type, rul], ...]
            if tool['License']!='':
                newInst.license = [tool['License']] # string
            else:
                newInst.license = False
            newInst.authors = [a.lstrip() for a in tool['authors']] # list of strings
            newInst.repository = [tool['Source Repository'].split('gitclone')[1]]
            newInst.description = [tool['description']]
            newInst.source = ['bioconductor'] #string

            self.instSet.instances.append(newInst)
