import json
from FAIRsoft.utils import setOfInstances
from FAIRsoft.utils import instance
from FAIRsoft.transformation.meta_transformers import toolGenerator
from FAIRsoft.transformation.meta_transformers import clean_version
from FAIRsoft.transformation.meta_transformers import clean_name

class transformer(toolGenerator):
    def __init__(self, tools, source = 'biotoolsOPEB'):
        toolGenerator.__init__(self, tools, source)

        self.import_bioconda_dict()
        self.instSet = setOfInstances('biotoolsOPEB')

        for tool in self.tools:
            if tool['@label']:
                name = clean_name(tool['@label'])
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

                    self.instSet.instances.append(newInst)

    def import_bioconda_dict(self):
            with open('/home/eva/projects/FAIRsoft/FAIRsoft_ETL/FAIRsoft/FAIRsoft/transformation/bioconda_types.json', 'r') as infile:
                self.bioconda_types = json.load(infile)
