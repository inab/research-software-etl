from src.infrastructure.db.mongo.mongo_db_singleton import mongo_adapter

pattern = 'https://spdx.org/licenses/'

def is_normalized_license(license: dict) -> bool:
    """
    Check if the license is normalized.
    """
    if license.get('url'):
        return license['url'].startswith(pattern)
    

if __name__ == "__main__":
    normalized = 0
    total = 0
    licenses = 0
    for tool in mongo_adapter.fetch_entries("toolsDev", {}):
        if tool['data'].get('license'):
            total += 1
            for license in tool['data']['license']:
                licenses += 1
                if is_normalized_license(license):
                    normalized += 1
                

    print(f"Normalized licenses: {normalized}")
    print(f"Total records with license: {total}")
    print(f"Total licenses: {licenses}")
    print(f"Percentage of normalized licenses: {normalized / licenses * 100:.2f}%")
                    