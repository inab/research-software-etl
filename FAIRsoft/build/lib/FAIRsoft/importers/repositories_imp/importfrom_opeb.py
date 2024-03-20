import json
with open('metrics.json', 'r') as file_alam:
    alambique_opeb = json.load(file_alam)


for entry in alambique_opeb:
    if 'biotools' not in entry.keys():
        print(entry)
