from infrastructure.db.mongo.mongo_adapter import MongoDBAdapter

mongo_adapter = MongoDBAdapter()

pattern = "https://spdx.org"


def is_normalized_license(license_item: dict) -> bool:
    """
    Check if a license item is normalized.
    A license is considered normalized if its URL starts with the SPDX pattern.
    """
    url = license_item.get("url")
    return bool(url and url.startswith(pattern))


if __name__ == "__main__":
    normalized_licenses = 0
    total_records_with_license = 0
    total_licenses = 0
    normalized_records = 0

    for tool in mongo_adapter.fetch_entries("toolsDev", {}):
        license_list = tool.get("data", {}).get("license")

        if license_list:
            total_records_with_license += 1
            record_has_normalized_license = False

            for license_item in license_list:
                total_licenses += 1
                if is_normalized_license(license_item):
                    normalized_licenses += 1
                    record_has_normalized_license = True

            if record_has_normalized_license:
                normalized_records += 1

    print(f"Normalized licenses: {normalized_licenses}")
    print(f"Total records with license: {total_records_with_license}")
    print(f"Total licenses: {total_licenses}")
    print(
        f"Percentage of normalized licenses: "
        f"{normalized_licenses / total_licenses * 100:.2f}%"
        if total_licenses
        else "Percentage of normalized licenses: 0.00%"
    )
    print(
        f"Percentage of license-bearing records with normalized licenses: "
        f"{normalized_records / total_records_with_license * 100:.2f}%"
        if total_records_with_license
        else "Percentage of license-bearing records with normalized licenses: 0.00%"
    )