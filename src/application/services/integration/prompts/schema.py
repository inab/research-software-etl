schema = {
    "type": "object",
    "strict": True,
    "properties": {
      "verdict": {
        "type": "string",
        "enum": ["Unclear", "Yes", "No"]
      },
      "groups": {
        "type": "array",
        "items": {
          "type": "array",
          "items": {
            "type": "string"
          }
        }
      },
      "message": {
        "type": "string"
      },
      "github_issue": {
        "type": "object",
        "properties": {
          "title": {
            "type": "string"
          },
          "body": {
            "type": "string"
          }
        },
        "required": ["title", "body"]
      }
    },
    "required": ["verdict", "groups", "message"]
  }
  