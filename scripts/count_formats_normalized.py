from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


def is_normalized_format(format: dict, source: list) -> bool:
    if 'biotools' not in source:
        return False
    
    else:
        if format.get('uri'):
            return True
        else:
            if format.get('datatype')['uri']:
                return True
            
    return False



if __name__ == "__main__":
    normalized = 0
    unique_ids = set()

    for tool in mongo_adapter.fetch_entries("pretoolsDev", {}):
        if tool['data'].get('input'):
            for input in tool['data']['input']:
                if is_normalized_format(input, tool['data']['source']):
                    normalized += 1
                    unique_ids.add(tool['_id'])

        if tool['data'].get('output'):
            for output in tool['data']['output']:
                if is_normalized_format(output, tool['data']['source']):
                    normalized += 1
                    unique_ids.add(tool['_id'])

    N = 0
    for tool in mongo_adapter.fetch_entries("toolsDev", {}):
        for source in tool.get('source'):
            if source in unique_ids:
                N += 1
                break
    


    print(f"Records with normalized formats: {N}")
    print(f"Total normalized formats: {normalized}")



