import unittest
import json 
import os

import FAIRsoft
from FAIRsoft.integration.run_integration import collect_pretools_instances
from FAIRsoft.integration.integration import build_pre_integration_dict
from FAIRsoft.integration.integration import create_integrated_instances

# test  run_integration.py        
class TestRunIntegration(unittest.TestCase):

        def test_collect_pretools_instances(self):
            with open('FAIRsoft/tests/data/pretools.json', 'r') as infile:
                pretools = json.load(infile)

            names = ['a4', 'a4base', 'a4classif', 'a4core', 'a4preproc', 'a4reporting', 'abaenrichment', 'abarray', 'absseq', 'abseqr']
            descriptions = []
            names = set(names)

            os.environ['BIOCONDUCTOR'] = 'True'
            insts = collect_pretools_instances(pretools, 'filesystem')
            calculated_names = []
            for source_list in insts:
                if source_list:
                    calculated_names.extend([inst.name for inst in source_list])
            
            #print(calculated_names)
            
            self.assertEqual(set(calculated_names), names)



# test integration.py
class TestIntegration(unittest.TestCase):
    
    def test_publications_integration(self):
        # input to test
        with open('FAIRsoft/tests/data/pretools_integration.json', 'r') as infile:
            pretools = json.load(infile)
        # correct output (integrated tool)
        with open('FAIRsoft/tests/data/tools_integration_assert.json', 'r') as infile:
            assert_tool = json.load(infile)
        
        STORAGE_MODE = 'filesystem'
        allInsts = collect_pretools_instances(pretools, STORAGE_MODE)
        
        totalNames, pre_integration_dict = build_pre_integration_dict(allInsts)
 

        ## Create integration intances. Returns a list of instances and log.
        resulting_tools, log = create_integrated_instances(pre_integration_dict, None, None)

        # --- For debugging purposes-----------------

        #print(json.dumps(resulting_tools[0], sort_keys=True, indent=4))
        #print('-----------------------------------------------------')
        #print(json.dumps(assert_tool[0], sort_keys=True, indent=4))

        #print('-----------------------------------------------------')


        for key,value in resulting_tools[0].items():
            if key not in assert_tool[0].keys():
                self.assertEqual(value, assert_tool[0][key])

        
