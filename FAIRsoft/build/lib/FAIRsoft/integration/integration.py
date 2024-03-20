import json
import pickle
import re
import logging
from munch import munchify

from FAIRsoft.utils import instance
from FAIRsoft.utils import setOfInstances
from FAIRsoft.utils import canonicalTool
from FAIRsoft.utils import canonicalSet
from FAIRsoft.utils import webTypes
from FAIRsoft.utils import update_entry, save_entry, push_entry

def save_obj(obj, name ):
    with open('obj/'+ name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def worker_pre_integration(i_n, inst, groupInst):
    name = inst.name
    if not inst.version:
        inst.version = 'unknown'
    if not inst.type:
        inst.type = 'unknown'

    if name in groupInst.keys():
        if inst.type in groupInst[name].keys():
            newList = groupInst[name][inst.type] + [inst]
            groupInst[name][ inst.type] = newList
        else:
            groupInst[name][inst.type]= [inst]  
    else:
        logging.debug(f"{inst.name} not in totalNames")
    
    return(groupInst)
    

def build_pre_integration_dict(setsOfInsts):
    '''
    input: setsOfInstances is a list of sets of instances
    by name and type
    '''
    totalNames = []
    names = []
    for instances in setsOfInsts:
        names.append(set([a.name for a in instances]))
        totalNames = totalNames + [ a.name for a in instances ]


    groupInst = dict()
    totalNames = set(totalNames)

    # Grouping the instances by name and type in a dictionary (groupInst)
    for name in totalNames: # iterating tool names 
        groupInst[name] = {}
    i_n = 0
    for set_ in setsOfInsts:
        for inst in set_:
            i_n+=1
            groupInst = worker_pre_integration(i_n, inst, groupInst)

    return(totalNames, groupInst)

# TODO
# Identify format
# Re-format
# Rmove duplicates
def identify_publication_format(pub):
    '''
    returns 'type'/'format' of publication information in entry
    possible formats types: 
        - 'oeb': typical OEB
        - 'key': { 'doi' : foo } or { 'pmid' : foo } or { 'pmid' : foo }
        - ''
    '''
    # OEB
    if type(pub) == dict:
        if 'entries' in pub:
            return('oeb')


def build_new_publication_meta(pubs_by_id):
    fields = ['doi','pmid','pmcid','url','citations','citation','title','year','journal','references','count']
    new_entry = {
            'doi':pubs_by_id.get('doi'),
            'pmid':pubs_by_id.get('pmid'),
            'pmcid':pubs_by_id.get('pmcid'),
            'url':None,
            'citations':None,
            'citation':None,
            'title':None,
            'year': None,
            'journal':None,
            'references':None,
            'count':None
        }
    for key in fields:
        key_found = False
        while key_found:
            for entry in pubs_by_id['entries']:
                if entry.get(key):
                    new_entry[key] = entry.get(key)
                    key_found = True

    return(new_entry)


def clean_reps_publications(publications):
    #unique_pubs_by_id = [{'ids': [doi, pmid, pmcid], 'entries':[publications]}]
    unique_pubs_by_id = []
    for pub_ in publications:
        if type(pub_) != list:
            pub_ = [pub_]
        for publication in pub_:
            #TODO extract ids if possible
            id_types = ['doi' ,'pmid', 'pmcid']
            # if doi/pmid/pmcid present

            publication = publication.__dict__

            ids_present = [id_type for id_type in id_types if id_type in publication.keys()]
            match = False
            while match:
                if ids_present:
                    for unique_entry in unique_pubs_by_id.keys():
                        for id_type in ids_present:
                            if publication[id_type] in unique_entry['ids']:
                                # publication already seen
                                if publication in unique_entry['entries']:
                                    # This publication DONE
                                    match = True
                                # publication not seen --> store
                                new_unique_by_id[unique_entry['entries']].append(publication)
                                # This publication DONE
                                match = True
                            
                    # If not in any unique_pubs_id[key]:
                    new_unique_by_id = {
                        'ids' : {
                            'doi':publication.get('doi'),
                            'pmid': publication.get('pmid'),
                            'pmcid': publication.get('pmcid')
                        },
                        'entries' : []
                    }
                    [publication.pop(id_type) for id_type in id_types]
                    new_unique_by_id.append(publication)

                    unique_pubs_by_id.append(new_unique_by_id)
                    # This publication DONE
                    match = True


                # if ids not present
                else:
                    new_unique_by_id = {
                        'ids' : {
                            'doi': None,
                            'pmid': None,
                            'pmcid': None
                        },
                        'entries' : [publication]
                    }
                    unique_pubs_by_id.append(new_unique_by_id)
                    match = True

        # Building publication instance def metadata:
        new_publications = []

        for pub in unique_pubs_by_id:
            new_publications.append(build_new_publication_meta(pub))

        return(new_publications)

def clean(item):
    if item == 'unknown':
        item = None
    if item == 'None':
        item = None
    
    return(item)

def clean_list(items_list):
    if None in items_list:
            items_list.remove(None)
    return(items_list)


def worker_integration(name, groupInst):
    new_insts = []
    for type_ in groupInst[name].keys():
       
        instaList =  groupInst[name][type_]
        version = [] 
        for a in instaList:
            if a.version:
                 version.append(clean(a.version[0]))
        version = list(set(version))
        
        newInst = instance(name, type_, version)

        newInst.label = [clean(a.label) for a in instaList if a.label]
        newInst.label = list(set(clean_list(newInst.label)))

        newInst.description = [clean(a.description[0]) for a in instaList if a.description] # constructing_consensus
        newInst.description = clean_list(newInst.description)

        newLinks = []
        for inst in instaList:
            for link in inst.links:
                if link not in newLinks and link:
                    newLinks.append(clean(link))
        newInst.links = clean_list(newLinks)

        
        pubs = []
        for pretool in instaList:
            if pretool.publication:
                for p in pretool.publication:
                    if p not in pubs:
                        pubs.append(clean(p))

        #newInst.publication =  clean_reps_publications(pubs)
        newInst.publication = clean_list(pubs)

        newInst.download = [clean(item) for sublist in instaList for item in sublist.download]  
        newInst.download = clean_list(newInst.download)

        inst_instr = [a.inst_instr for a in instaList]
        if True in inst_instr:
            newInst.inst_instr = True #
        else:
            newInst.inst_instr = False

        tests = [a.test for a in instaList]
        if True in tests:
            newInst.test = True #
        else:
            newInst.test = False

        newSrc = []
        for a in instaList:
            if a.src:
                for s in a.src:
                    if s!=None:
                        newSrc.append(clean(s))

        newInst.src = clean_list(newSrc)

        newOs = []
        for inst in instaList:
            if inst.os:
                for os in inst.os:
                    if os not in newOs:
                        newOs.append(clean(os))

        newInst.os = clean_list(newOs)


        newInputs = []
        for insta in instaList:
            if insta.input:
                for Dict in insta.input:
                    if Dict not in newInputs:
                        newInputs.append(clean(Dict))
                    else:
                        continue

        newInst.input = clean_list(newInputs) # list of strings/dicts
        # TODO: fix this inconsistency with input as strings or dicts in the generators

        newOutputs = []
        for insta in instaList:
            if insta.output:
                for Dict in insta.output:
                    if Dict not in newOutputs:
                        newOutputs.append(clean(Dict))
                    else:
                        continue
            # TODO: fix this inconsistency with output as strings or dicts in the generators

        newInst.output = clean_list(newOutputs) # list of strings

        newDep = []
        for inst in instaList:
            if inst.dependencies:
                for dep in inst.dependencies:
                    if dep not in newDep:
                        newDep.append(clean(dep))
        newInst.dependencies = clean_list(newDep) # list of strings

        newDocs = []
        for inst in instaList:
            if inst.documentation:
                for doc in inst.documentation:
                    if doc not in newDocs:
                        newDocs.append(clean(doc))
                    else:
                        continue

        newInst.documentation = clean_list(newDocs) # list of lists [[type, url], [type, rul], ...]

        newLicense = []
        for a in instaList:
            if a.license:
                for lic in a.license:
                    if lic:
                        if clean(lic) not in newLicense:
                            newLicense.append(clean(lic))
                else:
                    continue

        newInst.license = clean_list(newLicense)

        newInst.termsUse = False #
        newInst.contribPolicy = False

        newAuth  = []
        for l in instaList:
            if l.authors:
                for auth in l.authors:
                    try:
                        if clean(auth) and clean(auth.lstrip()) not in newAuth:
                            newAuth.append(clean(auth.lstrip()))
                        else:
                            continue
                    except Exception as e:
                        logging.error(e)
                        logging.error("Cannot clean authors:")
                        logging.error(l.authors)

        newInst.authors = clean_list(newAuth) # list of strings

        newRepos = []
        for t in instaList:
            if t.repository:
                for rep in t.repository:
                    if rep not in newRepos:
                        newRepos.append(clean(rep))
        newInst.repository = clean_list(newRepos)

        newSource = []
        for inst in instaList:
            if inst.source:
                for s in inst.source:
                    if s not in newSource:
                        newSource.append(clean(s))
        
        newInst.source = clean_list(newSource)
        
        newInst.operational = False
        newInst.ssl = False
        newInst.bioschemas = False
        for a in instaList:
            if a.operational == True:
                newInst.operational = True
            if a.ssl == True:
                newInst.ssl=True
            if a.bioschemas == True:
                newInst.bioschemas = True
        
        semantics = {'inputs':[],'outputs':[],'topics':[], 'operations':[]}
        for inst in instaList:
            if inst.semantics:
                for field in ['topics', 'operations', 'inputs', 'outputs']:
                    if inst.semantics[field]:
                        [semantics[field].append(item) for item in inst.semantics[field]]
        try:
            for field in ['topics', 'operations']:
                semantics[field] = list(set(semantics[field])) # remove duplic
        except Exception as e:
            logging.error("Error in merging semantics:")
            logging.error(f"Semantics: {semantics}")
            logging.error(f"Instances: {instaList}")

        newInst.semantics=semantics
        
        edam_topics = set()
        for inst in instaList:
            if inst.edam_topics:
                [edam_topics.add(item) for item in inst.edam_topics]
        
        newInst.edam_topics = list(edam_topics)

        edam_operations = set()
        for inst in instaList:
            if inst.edam_operations:
                [edam_operations.add(item) for item in inst.edam_operations]
        
        newInst.edam_operations = list(edam_operations)
        
        tags = set()
        for inst in instaList:
            if inst.tags:
                [tags.add(item) for item in inst.tags]
        newInst.tags = list(tags)

        # return instead of pushing to db
        inst=newInst.__dict__
        inst['@id'] = "https://openebench.bsc.es/monitor/tool/{name}:{version}/{type}".format(name=inst['name'], version=inst['version'], type=inst['type'])
        new_insts.append(inst)

    return(new_insts)


def integrate_types(groupOfInstances):
    types = list(groupOfInstances.keys())
    not_unknown_types = [type_ for type_ in  types if type_!='unknown']
    n_not_unknown = len(not_unknown_types)
    if n_not_unknown==1:
        known_type = not_unknown_types[0]
        new_known_insts = groupOfInstances[known_type] + groupOfInstances['unknown']
        groupOfInstances[known_type] = new_known_insts
        groupOfInstances.pop('unknown', None)
    return(groupOfInstances)


def create_integrated_instances(groupInst, out_resource, storage_mode='db'):
    # return resuting instances for testing purposes
    result = []
    n_i=0
    log = {
        'errors':[],
        'n_ok':0,
    }
    landmarks = {str(int((len(groupInst)/5)*i)): f"{i*10}%" for i in range(0,10)}
    # for each canonical tool name
    for name in groupInst.keys():
        n_i += 1
                
        if str(n_i) in landmarks.keys():
            logging.debug(f'{n_i}/{len(groupInst)} ({landmarks[str(n_i)]}) canonical tools processed\r')

        if 'unknown' in groupInst[name].keys():
            groupInst[name] = integrate_types(groupInst[name])
        
        integrated_insts = worker_integration(name, groupInst)
        
        # for each instance of the canonical tool, push to db or save to file
        for integrated_inst in integrated_insts:
            result.append(integrated_inst)

            if storage_mode=='db': 
                log = update_entry(integrated_inst, out_resource, log)
                #log = push_entry(integrated_inst, out_resource, log)
            elif storage_mode=='filesystem':
                log = save_entry(integrated_inst, out_resource, log)

    
    return(result, log)



def generateCanonicalSet(instsctDist):
    '''
    groups instances by name into canonicals
    input: {
             name1: [instance1, instance2],
             name2: [instance3],
             ...
             }
    output: canonicalSet
    '''
    newCanonSet  = canonicalSet()
    for name in instsctDist.keys():
        instances = instsctDist[name]
        sources = list(set([item for sublist in instances for item in sublist.source]))
        types = list(set([inst.type for inst in instances if inst.type != None ]))
        newCanon = canonicalTool(name, instances, sources, types)
        newCanonSet.addCanononical(newCanon)
    return(newCanonSet)



def loadJSON(path):
    with open(path) as fil:
        return(json.load(fil))

global stdFormats
def prepFAIRcomp(instances):
    stdFormats= getFormats(instances)
    return(stdFormats)
    
def get_stdFormats():
    return(stdFormats)


def getFormats(instances):
    inputs = [a.input for a in instances]
    inputs_ = [a for a in inputs]
    inputsNames = []

    nonSFormats = ['txt', 'text', 'csv', 'tsv', 'tabular', 'xml', 'json', 'nucleotide', 'pdf', 'interval' ]
    for List in inputs_:
        for eachD in List:
            if 'format' in eachD.keys():
                if ' format' not in eachD['format']['term'] and eachD['format']['term'].lstrip() not in nonSFormats:
                    if '(text)' not in eachD['format']['term']:
                        if eachD['format']['term'].lstrip() not in inputsNames:
                            inputsNames.append(eachD['format']['term'].lstrip())
    return(inputsNames)
