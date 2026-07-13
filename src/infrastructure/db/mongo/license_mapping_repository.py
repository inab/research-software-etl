# This repository connects to the SPDX license mapping collection.

from infrastructure.db.database_adapter import DatabaseAdapter


class LicenseMappingRepository:
    def __init__(
        self, db_adapter: DatabaseAdapter, collection_name: str = "licensesMapping"
    ):
        self.db_adapter = db_adapter
        self.collection_name = collection_name

    def find_spdx(self, name: str) -> dict | None:
        """
        Look a license name up against SPDX, by identifier, synonym or full name.

        Deprecated SPDX identifiers never match.
        """
        query = {
            "$or": [
                {"licenseId": name},
                {"synonyms": name},
                {"name": name},
            ],
            "isDeprecatedLicenseId": False,
        }
        return self.db_adapter.fetch_entry(self.collection_name, query)
