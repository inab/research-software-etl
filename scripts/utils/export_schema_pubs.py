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


from src.domain.models.software_instance.main import instance

# Generate the schema (as Python dict)
schema_dict = instance.model_json_schema()

# Save it to a JSON file
with open("software_instance.schema.json", "w") as f:
    json.dump(schema_dict, f, indent=2)

print("✅ Schema exported to software_instance.schema.json")