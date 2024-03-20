import unittest
import json 
import warnings


import FAIRsoft
import FAIRsoft.transformation.meta_transformers as meta_trans 

class TestMetaTransformers(unittest.TestCase):
    
    def test_biocondaRecipesGen(self):
        """
        Bioconda recipes to instances
        """
        with open('FAIRsoft/tests/data/bioconda_recipes.json', 'r') as datafile:
            data = json.load(datafile)
        
        biocondaGenerator = meta_trans.biocondaRecipesToolsGenerator(data)
        instances = biocondaGenerator.instSet.instances 

        # Correct number of instances and types
        assert_count_instances = {
            'thesias':{
                'insts':1, 
                'type':set(['cmd'])
                },
            'cmappy':{
                'insts': 2,
                'type':set(['lib', 'cmd'])
                },
            'ag.db' : {
                'insts':1,
                'type':set(['lib'])
            },
            'tbl2asn':{
                'insts':1, 
                'type':set(['cmd'])
            }
        }

        #  To test: Number of instances and types in generated instances
        test_count_instances = {}
        for inst in instances:
            if inst.name not in test_count_instances:
                test_count_instances[inst.name] = {
                    'insts': 1,
                    'type': set([inst.type])
                }
            else:
                test_count_instances[inst.name]['insts'] += 1
                test_count_instances[inst.name]['type'].add(inst.type)
        
        for  inst_name in test_count_instances:
            self.assertEqual(test_count_instances[inst_name], assert_count_instances[inst_name])

    def test_repository(self):
        '''
        Repository
        '''
        with open('FAIRsoft/tests/data/bioconda_recipes.json', 'r') as datafile:
            data = json.load(datafile)

        assert_repos = {
            'thesias' : ["https://github.com/daissi/thesias"],
            'cmappy' : ["https://github.com/cmap/cmapPy"],
            'ag.db' : [],
            'tbl2asn': []
        }
        
        biocondaGenerator = meta_trans.biocondaRecipesToolsGenerator(data)
        instances = biocondaGenerator.instSet.instances

        for inst in instances:
            self.assertEqual(inst.repository, assert_repos[inst.name])

    def test_type_dict(self):
        with open('FAIRsoft/tests/data/bioconda_recipes.json', 'r') as datafile:
            data = json.load(datafile)

        assert_dict = {
            'thesias': ['cmd'],
            'cmappy': ['lib', 'cmd'], 
            'ag.db': ['lib'],
            'tbl2asn': ['cmd']
            }

        biocondaGenerator = meta_trans.biocondaRecipesToolsGenerator(data)
        self.assertEqual(biocondaGenerator.type_dictionary(None), assert_dict)
    
    def test_OPEB_conda_types(self):
        '''
        Types from OPEB, OPEB metrics and conda that are also 
        present in bioconda recipes are assigned the recipe's type 
        in transformation steps
        '''
        with open('FAIRsoft/tests/data/bioconda_transform.json', 'r') as datafile:
            data_al = json.load(datafile)

        assert_dict = {
            "rbcbook1": ["lib"],
            "fastq-filter": ["lib", "cmd"],
            "gargammel-slim": ["cmd"]
            }

        entries = {}

        for source in meta_trans.tool_generators:
            entries[source] = []

        for entry in data_al:
            if entry.get('@data_source') != None:
                for s in entries:
                    if entry['@data_source'] == s:
                        entries[s].append(entry)
        
        for source in entries:
            # the following sources must have the same type
            if source in ['conda', 'opeb_metrics', 'bioconda', 'bioconda_conda', 'bioconda_recipes']:
                if entries[source]:
                    generator = meta_trans.tool_generators[source](entries[source])
                    for inst in generator.instSet.instances:
                        self.assertIn(inst.type, assert_dict[inst.name])
            else:
                if entries[source]:
                    generator = meta_trans.tool_generators[source](entries[source])
                    for inst in generator.instSet.instances:
                        if inst.type not in assert_dict[inst.name]:
                            msg = f'\nType of "{inst.name}" according to:\n - bioconda recipe: {assert_dict[inst.name]}\n - biotools: {inst.type}\n'
                            warnings.warn(msg)
        
    def test_repostIntegrationType(self):
        '''
        Metadata from repositories is assigned the correct type
        bioconda - according to bioconda recipes
        galaxy - if original is 'workflow', then replace with cmd.
        else - keep the type as in the @id
        '''
        with open('FAIRsoft/tests/data/repository_transform.json', 'r') as datafile:
            data = json.load(datafile)

        assert_dict = {
            "https://openebench.bsc.es/monitor/tool/repository:bridge-galaxy/workbench" : 'workbench',
            "https://openebench.bsc.es/monitor/tool/repository:bridge-galaxy/workflow" : 'cmd',
            "https://openebench.bsc.es/monitor/tool/repository:bridge-galaxy": None
        }

        reposGenerator = meta_trans.repositoryToolsGenerator(data)
        instances = reposGenerator.instSet.instances

        for entry in data:
            reposGenerator = meta_trans.repositoryToolsGenerator([entry])
            instances = reposGenerator.instSet.instances
            id_ = entry['@id']
            if instances:
                self.assertEqual(instances[0].type, assert_dict[id_])
            else:
                self.assertEqual(None, assert_dict[id_])

    def test_publications_obeb_metrics(self):
        '''
        opeb metrics publications must be transformed to a list ob objects
        [
            {
                cit_count: ...,
                doi: ...,
                pmcid: ...,
                year: ...,
                citations: ...,
                ...
            }
        ]
        '''
        with open('FAIRsoft/tests/data/opeb_pubs_transform.json', 'r') as datafile:
            data_al = json.load(datafile)
        
        opeb_metrics_Generator = meta_trans.metricsOPEBToolsGenerator(data_al)
        instances = opeb_metrics_Generator.instSet.instances
        inst = instances[0]
        publications = inst.publication
        for pub in publications:
            #print(pub.keys())
            self.assertEqual(type(pub), dict)




if __name__ == '__main__':
    unittest.main()