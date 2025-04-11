import json

# Define paths
input_path = "scripts/evaluation/messages_chat_old.jsonl"
output_path = "scripts/evaluation/messages_chat.jsonl"

# Define the replacement content
replacement_text = (
    "All parts have been sent. Please now analyze the entries and provide the output as specified.\n\n"
    "IMPORTANT: Return ONLY a valid Python dictionary with the following keys: 'verdict', 'explanation', "
    "'confidence', and 'features'. Do NOT explanation, or extra commentary. "
    "This is a strict output constraint."
)

with open(input_path, "r", encoding="utf-8") as infile, open(output_path, "w", encoding="utf-8") as outfile:
    for line in infile:
        data = json.loads(line)
        case_id, messages = next(iter(data.items()))

        # Reverse search for the target user message
        for msg in reversed(messages):
            if msg.get("role") == "user" and "All parts have been sent" in msg.get("content", ""):
                msg["content"] = replacement_text
                break  # Only replace the last matching one

        # Write updated line
        updated_line = json.dumps({case_id: messages}, ensure_ascii=False)
        outfile.write(updated_line + "\n")

print(f"All matching final messages updated. Output saved to '{output_path}'.")