import json
import re
import logging
import bibtexparser

from FAIRsoft.utils import setOfInstances
from FAIRsoft.utils import instance

class toolGenerator(object):
    def __init__(self, tools, source):
        self.tools = tools
        self.source = source
        logging.debug('Generator for ' + self.source + ' initialized') 

# --------------------------------------------
# Functions used by several transformations
# --------------------------------------------

def clean_version(version):
    if version != None:
        if '.' in version:
            return(version.split('.')[0]+'.'+ version.split('.')[1])
        else:
            return(version)
    else:
        return(version)


def clean_name(name):
    bioconductor=re.search("^bioconductor-", name)
    if bioconductor:
        name=name[bioconductor.end():]
    emboss_dots=re.search("^emboss: ", name)
    if emboss_dots:
        name=name[emboss_dots.end():]
    emboss_unders=re.search("^emboss__", name)
    if emboss_unders:
        name=name[emboss_unders.end():]
    return(name)


def extract_ids(id_):
    #extract ids from metrics @id
    fields = id_.split('/')
    if len(fields)>6:
        name = fields[5].split(':')[1]
        if len(fields[5].split(':'))>2:
            version = fields[5].split(':')[2]
            source = fields[5].split(':')[0]
        else:
            version = None
            source = fields[5].split(':')[0]
        type_ = fields[6]
    
        ids = {
            'name' : name,
            'version' : version,
            'type' : type_,
            'source': source
        }

        return(ids)
    
    return(False)


def get_repo_name_version_type(id_):
    fields = id_.split('/')
    name_plus = fields[5]
    name_plus_fields=name_plus.split(':')
    name=name_plus_fields[1]
    if len(name_plus_fields)>2:
        version=name_plus.split(':')[2]
    else:
        version=None 

    if len(fields)>6:
        type_=fields[6]
    else:
        type_=None
     
    return({'name':name, 'version':version, 'type':type_})

# --------------------------------------------------------------
#   TRANSFORMERS
# --------------------------------------------------------------

# --------------------------------------------------------------
# Repository transformer 
# --------------------------------------------------------------
class repositoryToolsGenerator(toolGenerator):
    def __init__(self, tools, source = 'repository'):
        toolGenerator.__init__(self, tools, source)
        self.instSet = setOfInstances('repository')
        self.import_bioconda_dict()

        for tool in self.tools:
            # We skip generic entries
            if len(tool['@id'].split('/'))<7:
                continue

            else:
                id_data = get_repo_name_version_type(tool['@id'])
                name = clean_name(id_data['name'].lower())
                version = id_data['version']
                if version == None:
                    version = 'unknown'

                types_=[id_data['type']]

                if self.bioconda_types.get(name):
                    types_ = self.bioconda_types[name]
                
                if id_data['type'] == 'workflow' and 'galaxy' in tool['@id']:
                    types_=['cmd']

                for type_ in types_:

                    newInst = instance(name, type_, [version])
                    # there are several versions, to simplify integration, we want one instance per version
                    if 'versions' in  tool['repos'][0]['res'].keys():
                        versions = tool['repos'][0]['res']['versions']
                    else:
                        versions = [version]

                    for v in versions:
                        newInst = instance(name, type_, versions)

                        newInst.label = clean_name(id_data['name'])
                        

                        if tool['repos'][0]['res'].get('desc'):
                            newInst.description = [tool['repos'][0]['res'].get('desc')]
                        newInst.links = tool['entry_links']
                        newInst.publication =  []

                        binary_uri = tool['repos'][0]['res'].get('binary_uri')
                        source_uri = tool['repos'][0]['res'].get('source_uri')
                        download = [binary_uri, source_uri]
                        if None in download:
                            download.remove(None)
                        if source_uri or binary_uri:
                            newInst.download = download
                        else:
                            newInst.download = []  # list of lists: [[type, url], [], ...]
                        
                        newInst.inst_instr =  tool['repos'][0]['res'].get('has_tutorial')
                        newInst.test = None
                        try:
                            src = [tool['repos'][0]['res'].get('source_uri')]
                        except:
                            newInst.src = []
                        else:
                            if tool['repos'][0]['res'].get('source_uri')!=None:
                                newInst.src = src

                        if newInst.src:
                            newInst.os = ['Linux', 'Mac', 'Windows']
                        else:
                            newInst.os = None

                        newInst.input = None # list of dictionaries biotools-like {'format' : <format> , 'uri' : <uri> , 'data' : <data> , 'uri': <uri>}
                        newInst.output = None  # list of dictionaries biotools-like {'format' : <format> , 'uri' : <uri> }
                        newInst.dependencies = None # list of strings
                        if tool['repos'][0]['res'].get('readmeFile'):
                            newInst.documentation = [['readme', tool['repos'][0]['res'].get('readmeFile')]] # list of lists [[type, url], [type, rul], ...]
                        if tool['repos'][0]['res'].get('source_license'):
                            newInst.license = [tool['repos'][0]['res'].get('source_license')] 
                            newInst.termsUse = [tool['repos'][0]['res'].get('source_license')] 
                        newInst.contribPolicy = None

                        auths = []
                        authors_l = tool['repos'][0]['res'].get('tool_developers')
                        if authors_l:
                            for author in authors_l:
                                auths.append(author.get('username', None))
                        newInst.authors = auths

                        newInst.repository = tool['entry_links']
                        newInst.source = [tool['repos'][0]['kind']] #string
                        newInst.bioschemas = None
                        newInst.https = None
                        newInst.operational = None
                        newInst.ssl = None
                
                        self.instSet.instances.append(newInst)
    

    def import_bioconda_dict(self):
        '''
        TODO: the path to bioconda_dict should be a parameter
        '''
        path = './bioconda_types.json'
        logging.info('Importing bioconda types from: ' + path)
        with open(path, 'r') as infile:
            self.bioconda_types = json.load(infile)


# --------------------------------------------------------------
# Bioconda recipes tranformer 
# --------------------------------------------------------------
class biocondaRecipesToolsGenerator(toolGenerator):
    def __init__(self, tools, source="bioconda_recipes"):
        toolGenerator.__init__(self, tools, source)
        self.instSet = setOfInstances('bioconda_recipes')

        for tool in self.tools:
            name = clean_name(tool['name']).lower()
            version = tool['@id'].split('/')[5].split(':')[2]
            #print(tool)
            types_ = tool['type']
            if not types_:
                types_ =  ['cmd']

            if version == None:
                version = None
            
            for type_ in types_:
            
                newInst = instance(name, type_, [version])
                try:
                    description = tool['about']['description']
                except:
                    newInst.description = []
                else:
                    if description:
                        newInst.description = [description] # string
                
                newInst.label = clean_name(tool['name'])
                
                links = []
                if 'about' in tool.keys() and tool['about']:
                    if 'home' in tool['about'].keys() and tool['about']['home']:
                        if tool['about']['home']:
                            links.append(tool['about']['home'])
            
                src = []
                if tool.get('source'):
                    if type(tool.get('source')) == dict:
                        tool['source'] = [tool['source']]
                    for block in tool['source']:
                        if block.get('url'):
                            src = block['url']
                            if type(block['url'])==list:
                                for l in block['url']:
                                    links.append(l)

                            else:
                                links.append(block['url'])
                
                try:
                    doc_url = tool['about']['doc_url']
                except:
                    pass
                else:
                    if doc_url:
                        for d in doc_url:
                            links.append(d)

                # publications
                newInst.links = links

                new_pubids = set()
                if tool.get('extra'):
                    if tool['extra'].get('identifiers'):
                        for ident in tool['extra'].get('identifiers'):
                            reg1 = r'https:\/\/doi.org\/(10.([\w.]+?)\/([\w.]+)([\w.\/]+)?)'
                            reg2 = r'doi:(10.([\w.]+?)\/([\w.]+)([\w.\/]+)?)'
                            m1 = re.match(reg1, ident)
                            m2 = re.match(reg2, ident)
                            if m1:
                                new_pubids.add(m1.group(1))
                            if m2:
                                new_pubids.add(m2.group(1))

                    if tool['extra'].get('doi'):
                        for doi in tool['extra'].get('doi'):
                            new_pubids.add(doi)
                
                new_pubs = []
                for unique_id in new_pubids:
                    new_pubs.append({'doi':unique_id})

                newInst.publication =  new_pubs
                if src:
                    if type(src) != list:
                        src = [src]
                    
                    newInst.download = src
                    
                newInst.inst_instr = True # boolean // FUTURE: u'ri or text
                newInst.test = None
                newInst.src = src # string
                newInst.os = ['Linux', 'Mac', 'Windows'] # list of strings
                newInst.input = [] # list of dictionaries biotools-like {'format' : <format> , 'uri' : <uri> , 'data' : <data> , 'uri': <uri>}
                newInst.output = [] # list of dictionaries biotools-like {'format' : <format> , 'uri' : <uri> }
                deps = [] 
                if 'requirements' in tool.keys() and tool['requirements']:
                    for req_k in tool['requirements'].keys():
                        if tool['requirements'][req_k]:
                            for dep in tool['requirements'][req_k]:
                                deps.append(dep)

                newInst.dependencies = deps # list of strings
                documentation = []
                try:
                    doc = ['documentation',tool['about']['docs']]
                    documentation.append(doc)
                except:
                    pass

                try:
                    doc = ['documentation', tool['about']['doc_url']]
                    documentation.append(doc)
                except:
                    pass

                newInst.documentation = documentation # list of lists [[type, url], [type, rul], ...]
                if 'about' in tool.keys():
                    if tool['about'].get('license'):
                        newInst.license = [tool['about'].get('license')] 
                        newInst.termsUse = [tool['about'].get('license')] #
                newInst.contribPolicy = False
                credit = []
                try:
                    auth=tool['about']['author']
                except:
                    pass
                else:
                    credit.append(auth)
                try:
                    mantainers = tool['about']['mantainers']
                except:
                    mantainers = None
                else:
                    for m in mantainers:
                        credit.append(m)

                newInst.authors = credit # list of strings
                repository = set()
                for l in links:
                    if l:
                        if 'github' in l:
                            reg = r'^(https?:\/\/)?(www)?\b(github.com)\/[^/]*\/[^/]*'
                            m = re.match(reg, l)
                            if m:
                                repository.add(m.group())
                        #TODO: clean remaining repo extraction
                        elif 'bitbucket' in l:
                            repository.add(l)
                        elif 'sourceforge' in l:
                            repository.add(l)

                newInst.repository = list(repository)
                newInst.source = ['bioconda_recipes'] #string
                newInst.bioschemas = None
                newInst.https = None
                newInst.operational = None
                newInst.ssl = None

                self.instSet.instances.append(newInst)
    

    def type_dictionary(self, outpath):
        instances_types = {}
        for inst in self.instSet.instances:
            if inst.name in instances_types:
                instances_types[inst.name].append(inst.type)
            else:
                instances_types[inst.name] = [inst.type]
        
        if outpath:
            with open(outpath, 'w') as out_file:
                json.dump(instances_types, out_file)

        return(instances_types)

#--------------------------------------------
# Bioconda Conda Transformer
#--------------------------------------------

class bioconda_conda_ToolsGenerator(toolGenerator):
    def __init__(self, tools, source = 'bioconda_conda'):
        toolGenerator.__init__(self, tools, source)
        self.import_bioconda_dict()
        self.instSet = setOfInstances('bioconda_conda')

        for tool in self.tools:
            id_info = extract_ids(tool['@id'])
            name = clean_name(id_info['name']).lower()
            version = id_info['version']
            if version == None:
                version = 'unknown'
    
            if self.bioconda_types.get(name):
                types_ = self.bioconda_types[name]
            else:
                types_ = ['cmd']

            for type_ in types_:
                newInst = instance(name, type_, [version])

                newInst.label = clean_name(id_info['name']) # string
                newInst.description = None # string
                newInst.version = [version]
                newInst.type = type_
                newInst.links =[tool['url']]
                newInst.publication =  [] # number of related publications [by now, for simplicity]
                newInst.download = [tool['url']]  # list of lists: [[type, url], [], ...]
                newInst.inst_instr = True # boolean // FUTURE: uri or text
                newInst.test = None # boolean // FUTURE: uri or text
                newInst.src = [] # string
                newInst.os = ['Linux', 'Mac', 'Windows'] # list of strings
                newInst.input = [] # list of dictionaries biotools-like {'format' : <format> , 'uri' : <uri> , 'data' : <data> , 'uri': <uri>}
                newInst.output = [] # list of dictionaries biotools-like {'format' : <format> , 'uri' : <uri> }
                newInst.dependencies = tool['dependencies'] # list of strings
                newInst.documentation = [] # list of lists [[type, url], [type, rul], ...]
                if 'license' in tool.keys():
                    newInst.license = [tool['license']] # string
                newInst.termsUse = None #
                newInst.contribPolicy = None
                newInst.authors = [] # list of strings
                newInst.repository = []
                newInst.source = ['bioconda_conda'] #string
                newInst.bioschemas = None
                newInst.https = None
                newInst.operational = None
                newInst.ssl = None

                self.instSet.instances.append(newInst)

    def import_bioconda_dict(self):
            with open('./bioconda_types.json', 'r') as infile:
                self.bioconda_types = json.load(infile)

# --------------------------------------------
# Bioconda Tools Transformer
# --------------------------------------------
class biocondaToolsGenerator(toolGenerator):
    def __init__(self, tools, source = 'bioconda'):
        toolGenerator.__init__(self, tools, source)

        self.import_bioconda_dict()
        self.instSet = setOfInstances('bioconda')

        #names = [a['name'].lower() for a in self.tools]
        #print('diferent names in bioconda tools: ' + str(len(set(names))))

        for tool in self.tools:
            name = clean_name(tool['@label']).lower()
            
            version = clean_version(tool['@version'])
            if version == None:
                version = 'unknown'
            
            if self.bioconda_types.get(name):
                    types_ = self.bioconda_types[name]
            else:
                types_ = ['cmd']
                
            for type_ in types_:
                newInst = instance(name, type_, [version])

                newInst.label = clean_name(tool['@label']) # string

                if 'description' in tool.keys():
                    newInst.description = [tool['description']] # string
                if tool['web']['homepage']:
                    newInst.links = [tool['web']['homepage']] #list
                else:
                    newInst.links = []
                
                #print(tool['publications'] )
                newInst.publication =  tool['publications'] 

                download = []
                for k in tool['distributions'].keys():
                    for link in tool['distributions'][k]:
                        download.append(link)

                newInst.download = download

                newSrc = []
                for down in tool['distributions'].keys():
                    if 'source' in down:
                        if len(tool['distributions'][down])>0:
                            for u in tool['distributions'][down]:
                                newSrc.append(u)
                newInst.src = newSrc 

                if 'license' in tool.keys() and tool['license']!='':
                    newInst.license = [tool['license']] # string
                newInst.repository = tool['repositories']
                newInst.source = ['bioconda']
                newInst.links.append(tool['web']['homepage'])
                if tool['repositories']:
                    for a in tool['repositories']:
                        newInst.links.append(a)

                self.instSet.instances.append(newInst)
        

    def import_bioconda_dict(self):
            with open('./bioconda_types.json', 'r') as infile:
                self.bioconda_types = json.load(infile)


def constrFormatsConfig(formatList):
    '''
    From an input that is a str to a biotools kind of format
    '''
    notFormats = ['data']
    newFormats = []
    seenForms = []
    for formt in formatList:
        if formt not in seenForms:
            if ',' in formt:
                formats = formt.split(',')
                for f in formats:
                    if f not in notFormats:
                        newFormats.append({ 'format' : {'term' : f , 'uri' :  None }})
                        seenForms.append(formt)
            else:
                if formt not in notFormats:
                    newFormats.append({ 'format' :  {'term' : formt , 'uri' :  None }})
                    seenForms.append(formt)
        else:
            continue
    return(newFormats)


# --------------------------------------------
# Biotools OPEB Tools Transformer
# --------------------------------------------

class biotoolsOPEBToolsGenerator(toolGenerator):
    def __init__(self, tools, source = 'biotoolsOPEB'):
        toolGenerator.__init__(self, tools, source)

        self.import_bioconda_dict()
        self.instSet = setOfInstances('biotoolsOPEB')

        for tool in self.tools:
            if tool['@label']:
                name = clean_name(tool['@label']).lower()
                type_ = tool['@type']
                version = clean_version(tool['@version'])

                if self.bioconda_types.get(name):
                    types_ = self.bioconda_types[name]
                elif type_ == 'workflow' and 'galaxy' in tool['@id']:
                    types_=['cmd']
                else:
                    types_ = [type_]

                for type_ in types_:
                
                    if version == None:
                        version = 'unknown'
                    if type_ == None:
                        type_ = 'unknown'

                    newInst = instance(name, type_, [version])

                    newInst.label = clean_name(tool['name']) # string

                    newInst.description = [tool['description']] # string

                    newInst.publication = tool['publications']
                    newInst.test = False
                    if 'license' in tool.keys():
                        newInst.license = [tool['license']]
                    newInst.input = []
                    newInst.output = []
                    if 'documentation' in tool.keys():
                        if 'general' in tool['documentation'].keys():
                            newInst.documentation = [['general', tool['documentation']['general']]]
                    newInst.source = ['biotools']
                    os = []
                    if 'os' in tool.keys():
                        for o in tool['os']:
                            os.append(o)
                        newInst.os = os
                    newInst.repository = tool['repositories']

                    newInst.links.append(tool['web']['homepage'])
                    if tool['repositories']:
                        for a in tool['repositories']:
                            newInst.links.append(a)


                    if tool['semantics']:
                        newInst.input = tool['semantics'].get('inputs', [])
                        newInst.output = tool['semantics'].get('outputs', [])
                        newInst.edam_topics = tool['semantics'].get('topics',[])
                        newInst.edam_operations = tool['semantics'].get('operations',[])
                        newInst.semantics = tool['semantics']

                    newAuth = []
                    for dic in tool['credits']:
                        if dic.get('name'):
                            if dic['name'] not in newAuth and dic['name']!=None:
                                newAuth.append(dic['name'])
                    newInst.authors = newAuth
                    
                    newInst.tags = tool['tags'] 

                    self.instSet.instances.append(newInst)

    def import_bioconda_dict(self):
            with open('./bioconda_types.json', 'r') as infile:
                self.bioconda_types = json.load(infile)


# --------------------------------------------
# SourceForge Transformer
# --------------------------------------------
class sourceforgeToolsGenerator(toolGenerator):
    def __init__(self, tools, source = 'sourceforge'):
        toolGenerator.__init__(self, tools, source)

        self.instSet = setOfInstances('sourceforge')

        for tool in self.tools:
            name = tool['@source_url'].split('/')[-1]
            
            name = name.lower()
            type_ = 'unknown'
            version = 'unknown'

            newInst = instance(name, type_, [version])

            newInst.label = tool['name'] # string

            newInst.source = ['sourceforge']
            os = []
            if 'operating_system' in tool.keys():
                for o in tool['operating_system']:
                    os.append(o)
                newInst.os = os
            newInst.repository = [tool['repository']]
            newInst.download = [tool['@source_url']]
            newInst.repository = [tool['@source_url']]
            newInst.links.append(tool['homepage'])
            newInst.description = [tool.get('description')]
            newInst.license = tool['license']

            self.instSet.instances.append(newInst)


# --------------------------------------------
# Galaxy Transformer
# --------------------------------------------
class galaxyOPEBToolsGenerator(toolGenerator):
    def __init__(self, tools, source = 'galaxyOPEB'):
        toolGenerator.__init__(self, tools, source)

        self.instSet = setOfInstances('galaxyOPEB')

        for tool in self.tools:
        
            name = clean_name(tool['@label']).lower()
            name=name.replace(' ','_') #so it is coherent with opeb metrics names

            type_ = 'cmd'
            version = tool['@version']
            if version == None:
                version = 'unknown'

            newInst = instance(name, type_, [version])

            newInst.label = clean_name(tool['name']) # string
            newInst.description = [tool['description']] # string
            newInst.source = ['galaxy']
            newInst.os = ['Mac', 'Linux']
            newInst.repository = tool['repositories']
            if 'license' in tool.keys():
                newInst.license = [tool['license']]
            newInst.publication = tool['publications']

            self.instSet.instances.append(newInst)


# --------------------------------------------
# OPEB Metrics Transformer
# --------------------------------------------
class metricsOPEBToolsGenerator(toolGenerator):
    def __init__(self, tools, source = 'opeb_metrics'):
        toolGenerator.__init__(self, tools, source)
        self.import_bioconda_dict()
        self.instSet = setOfInstances('opeb_metrics')
        more_pubs = 0
        more_entries = 0
        for tool in self.tools:
            ids = extract_ids(tool['@id'])
            if ids:
                version = ids['version']
                
                # type needs to be corrected for galaxy tools from workflow to web
                
                if version == None:
                    version = 'unknown'
                name = clean_name(ids['name']).lower()

                if self.bioconda_types.get(name):
                    types_ = self.bioconda_types[name]
                elif ids['type'] == 'workflow' and 'galaxy' in tool['@id']:
                    types_=['cmd']
                else:
                    types_ = [ids['type']]
                
                for type_ in types_:
                    newInst = instance(name, type_, [version])
                    newInst.label = clean_name(ids['name']) # string
                    newInst.source = ['opeb_metrics']
                    if tool['project'].get('website'):
                        newInst.bioschemas = tool['project']['website'].get('bioschemas')
                        newInst.https = tool['project']['website'].get('https')
                        newInst.ssl = tool['project']['website'].get('ssl')
                        if tool['project']['website'].get('operational') == 200:
                            newInst.operational = True
                        else:
                            newInst.operational = False

                    pubs_new= []
                    if tool['project']['publications']:
                        for pub in tool['project']['publications']:
                            if pub.get('entries'):
                                for entry in pub.get('entries'):
                                    pubs_new.append(entry)
                                if len(pub['entries']) > 1:
                                    more_entries += 1

                        if len(tool['project']['publications'])>1:
                            more_pubs += 1
                        
                        newInst.publication = pubs_new
                    else:
                        newInst.publication = []
                    
                    

                    self.instSet.instances.append(newInst)
        
        logging.debug(f"Entries with more than one publications (entry.project.publication): {more_pubs}")
        logging.debug(f"Publications with more than one entry (entry.project.publication[i].entries) {more_entries}")

    def import_bioconda_dict(self):
        with open('./bioconda_types.json', 'r') as infile:
            self.bioconda_types = json.load(infile)


# --------------------------------------------
# Galaxy Transformer
# --------------------------------------------
class galaxyShedToolsGenerator(toolGenerator):
    def __init__(self, tools, source = 'galaxyShed'):
        toolGenerator.__init__(self, tools, source)

        self.instSet = setOfInstances('toolshed')

        for tool in self.tools:
            name = clean_name(tool['name']).lower()
            type_ = 'cmd'
            if 'version' in tool.keys():
                version = clean_version(tool['version'])
            else:
                version = 'unknown'

            newInst = instance(name, type_, [version])

            newInst.label = clean_name(tool['name'])
            newInst.description = [tool['description']] # string
            newInst.inst_instr = True # Since this is installable through ToolShed
            if len(tool['tests'])>0:
                newInst.test = True # boolean
            else:
                newInst.test = False

            newInst.dependencies = [a['name'] for a in tool['requirements']] # list of strings
            newInst.repository = [] #
            newInst.links = [] #
            newInst.source = ['toolshed']#string
            newInst.os = ['Linux', 'Mac']

            self.instSet.instances.append(newInst)

# --------------------------------------------
# Galaxy Metadata Transformer
# --------------------------------------------
class galaxyMetadataGenerator(toolGenerator):
    def __init__(self, tools, source = 'galaxy_metadata'):
        toolGenerator.__init__(self, tools, source)

        self.instSet = setOfInstances('galaxy_metadata')

        for tool in self.tools:
            name = clean_name(tool['name']).lower()
            type_ = 'cmd'
            if 'version' in tool.keys():
                version = clean_version(tool['version'])
            else:
                version = 'unknown'

            newInst = instance(name, type_, [version])

            newInst.label = clean_name(tool['name']) # string
            newInst.dependencies = tool['dependencies'] # list of strings
            newInst.source = ['galaxy_metadata']

            self.instSet.instances.append(newInst)

def parse_bibtex(ent):
    parser = bibtexparser.bparser.BibTexParser(common_strings=True)
    logger = logging.getLogger('bibtexparser')
    new_entries = []
    try:
        bibtexdb = bibtexparser.loads(ent, parser=parser)
        for entry in bibtexdb.entries:
            if entry['ENTRYTYPE'].lower() != 'misc':
                #print(entry)
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

# --------------------------------------------
# Galaxy Config Transformer
# --------------------------------------------
class galaxyConfigToolsGenerator(toolGenerator):
    def __init__(self, tools, source = 'toolshed'):
        toolGenerator.__init__(self, tools, source)

        self.instSet = setOfInstances('toolshed')

        for tool in self.tools:
            if tool['name']:
                name = clean_name(tool['name']).lower()

                type_ = 'cmd'

                version = clean_version(tool['version'])
                if version == None:
                    version = 'unknown'

                newInst = instance(name, type_, [version])

                newInst.label = clean_name(tool['name']) # string

                if tool['description']:
                    newInst.description = [tool['description']] # string

                new_pubs = []
                if tool['citation']:
                    if tool.get('citation'):
                        for cit in tool['citation']:
                            if cit.get('type') == 'doi':
                                new_pub = {'doi':cit.get('citation')}
                                new_pubs.append(new_pub)
                            else:
                                new_entries = parse_bibtex(cit.get('citation'))
                                for se in new_entries:
                                    new_pubs.append(se)

                    newInst.publication =  new_pubs

                newInst.test = tool['tests'] # boolean

                if len(tool['dataFormats']['inputs'])>0:
                    newInst.input = constrFormatsConfig(tool['dataFormats']['inputs']) # list of strings

                if len(tool['dataFormats']['outputs'])>0:
                    newInst.output = constrFormatsConfig(tool['dataFormats']['outputs']) # list of strings

                docu = []
                if tool['readme'] == True:
                    docu.append(['readme', None])
                if tool['help']:
                    docu.append(['help', tool['help'].lstrip()])

                newInst.documentation = docu # list of lists [[type, url], [type, url], ...]

                newInst.source = ['toolshed'] #string

                self.instSet.instances.append(newInst)



def lowerInputs(listInputs):
    newList = []
    if len(listInputs)>0:
        for format in listInputs:
            newFormat = {}
            for a in format.keys():
                newInner = {}
                if format[a] != []:
                    #print(format[a])
                    if type(format[a]) == list:
                        for eachdict in format[a]:
                            for e in eachdict.keys():
                                newInner[e] = eachdict[e].lower()
                            newFormat[a] = newInner
                    else:
                        for e in format[a].keys():
                            newInner[e] = format[a][e].lower()
                        newFormat[a] = newInner
        newList.append(newFormat)
    else:
        return([])
    return(newList)

# --------------------------------------------
# Bioconductor Transformer
# --------------------------------------------
class bioconductorToolsGenerator(toolGenerator):
    def __init__(self, tools, source='bioconductor'):
        toolGenerator.__init__(self, tools, source)

        self.instSet = setOfInstances('bioconductor')

        for tool in self.tools:
            type_= 'lib'
            version = clean_version(tool['Version'])
            if version == None:
                version = 'unknown'
            name = clean_name(tool['name']).lower()

            newInst = instance(name, type_, [version])

            newInst.label = clean_name(tool['name']) # string
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


tool_generators = {
        'bioconductor' : bioconductorToolsGenerator,
        'biotools' : biotoolsOPEBToolsGenerator,
        'bioconda' : biocondaToolsGenerator,
        'toolshed' : galaxyConfigToolsGenerator,
        'galaxy_metadata' : galaxyMetadataGenerator,
        'sourceforge' : sourceforgeToolsGenerator,
        'galaxy' : galaxyOPEBToolsGenerator,
        'opeb_metrics' : metricsOPEBToolsGenerator,
        'bioconda_recipes': biocondaRecipesToolsGenerator,
        'bioconda_conda': bioconda_conda_ToolsGenerator,
        'repository': repositoryToolsGenerator,
}


