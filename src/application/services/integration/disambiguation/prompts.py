import json
import logging
import tiktoken

from typing import List
from jinja2 import Template
from functools import lru_cache
from pathlib import Path


MAX_TOTAL_TOKENS = 130000  


# -------------------------------
# Tokenization Utilities
# -------------------------------


@lru_cache
def get_tokenizer(model="gpt-4"):
    return tiktoken.encoding_for_model(model)

def count_tokens(text, model="gpt-4") -> int:
    return len(get_tokenizer(model).encode(text))

def estimate_total_tokens(messages, model="gpt-4"):
    enc = get_tokenizer(model)
    return sum(len(enc.encode(msg["content"])) for msg in messages)


# -------------------------------
# Prompt + Chat Message Builder
# -------------------------------

def build_chat_messages_with_disconnected(
    instruction_prompt: str,
    conflict_data: dict,
    disconnected_preamble= "**Disconnected tools** to be analyzed",
    remaining_preamble= "Tools known to be the **same software**",
    max_tokens_per_chunk=8000,
    model="gpt-4"
):
    messages = [{"role": "user", "content": instruction_prompt}]
    enc = get_tokenizer(model)

    def chunk_entries(entries: List[dict]):
        chunks = []
        current_chunk = []
        current_token_count = 0

        for entry in entries:
            entry_json = json.dumps(entry, ensure_ascii=False)
            entry_tokens = len(enc.encode(entry_json))

            if current_token_count + entry_tokens > max_tokens_per_chunk:
                chunks.append(current_chunk)
                current_chunk = [entry]
                current_token_count = entry_tokens
            else:
                current_chunk.append(entry)
                current_token_count += entry_tokens

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def chunk_dict(d: dict):
        for url, content in d.items():
            for label, body in content.items():
                text = f"Content from {url}:\n```\n{label}:\n{body}```"
                yield {"role": "user", "content": text}

    # Add entries: known and disconnected tools
    if conflict_data.get("remaining"):
        for i, chunk in enumerate(chunk_entries(conflict_data["remaining"])):
            messages.append({
                "role": "user",
                "content": f"{remaining_preamble} - part {i+1}:\n```json\n{json.dumps(chunk, indent=2, ensure_ascii=False)}\n```"
            })

    if conflict_data.get("disconnected"):
        for j, chunk in enumerate(chunk_entries(conflict_data["disconnected"])):
            messages.append({
                "role": "user",
                "content": f"{disconnected_preamble} - part {j+1}:\n```json\n{json.dumps(chunk, indent=2, ensure_ascii=False)}\n```"
            })

    # Add enriched webpage and repository contents
    if "webpage_contents" in conflict_data:
        for chunk in chunk_dict(conflict_data["webpage_contents"]):
            messages.append(chunk)

    # Final instruction
    messages.append({
        "role": "user",
        "content": "All parts have been sent. Please now analyze the entries and provide the output as specified. \n\nIMPORTANT: Return ONLY a valid Python dictionary with the following keys: 'verdict', 'explanation', 'confidence', and 'features'. Do NOT explanation, or extra commentary. This is a strict output constraint."
    })

    # Token budget check
    total_tokens = estimate_total_tokens(messages, model=model)
    logging.info(f"Total tokens: {total_tokens}")
    if total_tokens > MAX_TOTAL_TOKENS:
        raise ValueError(f"Prompt too long: {total_tokens} tokens. Limit is {MAX_TOTAL_TOKENS}.")

    return messages

# -------------------------------
# Template Loader
# -------------------------------

def load_templates_from_folder(folder_path: str) -> dict:
    logging.info(f"Loading templates from folder: {folder_path}")
    templates = {}
    for file in Path(folder_path).glob("*.jinja2"):
        key = file.stem
        logging.info(f"Loading template: {key}")
        with open(file, encoding="utf-8") as f:
            templates[key] = Template(f.read())
    return templates


PROMPT_TEMPLATES = load_templates_from_folder("src/application/services/integration/prompts")


# -------------------------------
# Prompt Selection
# -------------------------------

def build_prompt(disconnected, remaining):

    template = PROMPT_TEMPLATES["prompt_benchmarking_chat_style"]

    instruction_prompt = template.render()

    data_dict = {
        "disconnected": disconnected,
        "remaining": remaining
    }

    return build_chat_messages_with_disconnected(instruction_prompt, data_dict)
