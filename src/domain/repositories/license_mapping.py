from typing import Optional, Protocol


class LicenseMappingRepository(Protocol):
    """The SPDX license-mapping collection."""

    def find_spdx(self, name: str) -> Optional[dict]:
        """Look a license name up against SPDX, by identifier, synonym or full name."""
        ...
