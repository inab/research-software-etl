from bson import json_util 

# open ../scripts/data/grouped_entries.json
with open('scripts/data/grouped_entries.json', 'r') as f:
    file_contents = f.read()

grouped_entries = json_util.loads(file_contents) 

# for the groups of entries in grouped_entries, get groups that contain non empty 
# publication fields. 

def get_non_empty_publication_groups(grouped_entries):
    non_empty_publication_groups = {}
    for key,group in grouped_entries.items():
        for instance in group['instances']:
            if instance['data']['publication']:
                non_empty_publication_groups[key] = group
                break
    
    return non_empty_publication_groups


# get nine groups from the grouped_entries that contain non empty publication fields. 
# each group should contain at least one intance from one of the following ['bioconda', 'bioconda_recipes', 'github', 'biotools', 'bioconductor', 'galaxy_metadata', 'toolshed', 'galaxy', 'sourceforge']
def get_group_with_inst_from_source(source, grouped_entries):
    for key,group in grouped_entries.items():
        for instance in group['instances']:
            if instance['data']['source'][0] == source:
                return { key: group }
                
    return 

def get_test_groups(non_empty_publication_groups):
    test_groups = {}
    for source in ['bioconda', 'bioconda_recipes', 'github', 'biotools', 'bioconductor', 'galaxy_metadata', 'toolshed', 'galaxy', 'sourceforge']:
        groups = get_group_with_inst_from_source(source, non_empty_publication_groups)
        if groups:
            test_groups.update(groups)

    return test_groups

    
if __name__ == '__main__':
    non_empty_publication_groups = get_non_empty_publication_groups(grouped_entries)
    print(f"Number of groups with non-empty publication fields: {len(non_empty_publication_groups)}")

    test_groups = get_test_groups(non_empty_publication_groups)
    print(f"Number of groups with non-empty publication fields and instances from sources: {len(test_groups)}")
    # export to json 

    with open('data/test_groups.json', 'w') as f:
        f.write(json_util.dumps(test_groups))

    #print(f"Test groups: {test_groups}")
