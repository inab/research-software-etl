from infrastructure.db.mongo.mongo_db_singleton import mongo_adapter


def map_license_item_to_spdx(license_item: dict) -> dict | None:
    """
    Normalize a single license item and map it to SPDX when possible.

    Rules:
    - Keep only items with a non-empty name.
    - If url is missing/null, try to map the license against licensesMapping.
    - Match against licenseId, synonyms, or name.
    - Ignore deprecated SPDX identifiers.
    - Return a normalized dict with keys: name, url.
    """
    if not isinstance(license_item, dict):
        return None

    name = license_item.get("name")
    url = license_item.get("url")

    if not isinstance(name, str) or not name.strip():
        return None

    name = name.strip()
    normalized_url = url.strip() if isinstance(url, str) and url.strip() else None

    normalized = {
        "name": name,
        "url": normalized_url,
    }

    query = {
        "$or": [
            {"licenseId": name},
            {"synonyms": name},
            {"name": name},
        ],
        "isDeprecatedLicenseId": False,
    }

    matching_license = mongo_adapter.fetch_entry("licensesMapping", query)

    if matching_license:
        normalized["name"] = matching_license["licenseId"]
        normalized["url"] = matching_license.get("reference")

    return normalized


def deduplicate_licenses_aggressively(licenses: list[dict]) -> list[dict]:
    """
    Remove duplicate licenses aggressively.

    Deduplication is done by normalized license name only.
    If several items collapse to the same name, keep the first one.
    """
    deduplicated = []
    seen_names = set()

    for license_item in licenses:
        name = license_item.get("name")
        if not isinstance(name, str) or not name.strip():
            continue

        normalized_name = name.strip()
        if normalized_name in seen_names:
            continue

        seen_names.add(normalized_name)
        deduplicated.append(
            {
                "name": normalized_name,
                "url": license_item.get("url"),
            }
        )

    return deduplicated


def normalize_license_field(license_field) -> list[dict]:
    """
    Normalize a tool license field into a deduplicated list of license items.
    """
    if license_field is None:
        return []

    if isinstance(license_field, dict):
        license_field = [license_field]

    if not isinstance(license_field, list):
        return []

    normalized = []
    for license_item in license_field:
        mapped = map_license_item_to_spdx(license_item)
        if mapped is not None:
            normalized.append(mapped)

    return deduplicate_licenses_aggressively(normalized)


def normalize_tool_licenses(tool: dict) -> list[dict]:
    """
    Normalize and deduplicate the license list of a tool document.
    """
    license_field = tool.get("data", {}).get("license", [])
    return normalize_license_field(license_field)