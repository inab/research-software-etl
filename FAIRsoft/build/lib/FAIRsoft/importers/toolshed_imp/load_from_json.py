import json
from pymongo import MongoClient

# connecting to DB
client = MongoClient(port=27017)
db = client.OPEB
alambique = db.alambique

with open("xml_metadatas.json", "r") as metadatasf:
    metadatas = json.load(metadatasf)

for main_tool in metadatas:
    for tool in main_tool:
        tool["data_source"] = "toolshed"
        alambique.insert_one(tool)
