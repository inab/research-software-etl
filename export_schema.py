# --- put this near the top of your script ---
from bson import ObjectId
from pydantic import GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
import json

# Tell Pydantic to render ObjectId as a string with a 24-hex pattern
def _objectid_json_schema(cls, _core_schema, _handler: GetJsonSchemaHandler) -> JsonSchemaValue:
    return {"type": "string", "pattern": "^[0-9a-fA-F]{24}$"}

# Monkey-patch the hook (no changes to your models needed)
ObjectId.__get_pydantic_json_schema__ = classmethod(_objectid_json_schema)
# --- end patch ---


from src.domain.models.database_entries import (
    PretoolsEntryModel,
    ToolEntryModel,
    PublicationEntryModel,
)


def export(model, name, title, description, doi_stub="10.5281/zenodo.YOUR_DOI"):
    """Generate and save a JSON Schema with descriptive metadata."""
    schema_dict = model.model_json_schema()

    # Add top-level JSON Schema metadata
    schema_dict.update({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"https://doi.org/{doi_stub}/{name}.schema.json",
        "title": title,
        "description": description,
    })

    # Save to file
    with open(f"{name}.schema.json", "w") as f:
        json.dump(schema_dict, f, indent=2)

    print(f"✅ Schema exported to {name}.schema.json")


# --- Export each Observatory schema ---

export(
    PretoolsEntryModel,
    "normalised_db_entry",
    title="Normalised Software Metadata Schema",
    description=(
        "Schema describing software metadata after normalization and harmonization "
        "within the Research Software Observatory. Records conform to a unified structure "
        "that enables consistent comparison and downstream integration."
    ),
)

export(
    ToolEntryModel,
    "Merged_db_entry",
    title="Merged Software Metadata Schema",
    description=(
        "Schema describing software metadata after blocking, disambiguation and merging"
        "within the Research Software Observatory. "
        "The difference with the normalized db entry is that type of software is an array and "
        "there is a new field: other_names"
    ),
)

export(
    PublicationEntryModel,
    "publication_entry",
    title="Publication Metadata Schema",
    description=(
        "Schema describing publication in the Research Software Observatory. "
    ),
)