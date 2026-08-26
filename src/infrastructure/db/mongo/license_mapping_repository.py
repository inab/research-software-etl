# This repository connects to the SPDX license mapping collection.

from infrastructure.db.database_adapter import DatabaseAdapter


class LicenseMappingRepository:
    def __init__(
        self, db_adapter: DatabaseAdapter, collection_name: str = "licensesMapping"
    ):
        self.db_adapter = db_adapter
        self.collection_name = collection_name
        self._index: dict[str, dict] | None = None

    def _build_index(self) -> dict[str, dict]:
        """
        Load the whole (non-deprecated) SPDX mapping once and index every
        license by identifier, synonym and full name.

        The collection is small and static during a run, so a single fetch
        replaces one DB round-trip per license lookup.
        """
        index: dict[str, dict] = {}
        for entry in self.db_adapter.fetch_entries(
            self.collection_name, {"isDeprecatedLicenseId": False}
        ):
            keys = [entry.get("licenseId"), entry.get("name")]
            synonyms = entry.get("synonyms") or []
            if isinstance(synonyms, list):
                keys.extend(synonyms)
            for key in keys:
                # First writer wins, mirroring fetch_entry returning one match.
                if isinstance(key, str) and key not in index:
                    index[key] = entry
        return index

    def find_spdx(self, name: str) -> dict | None:
        """
        Look a license name up against SPDX, by identifier, synonym or full name.

        Deprecated SPDX identifiers never match.
        """
        if self._index is None:
            self._index = self._build_index()
        return self._index.get(name)
