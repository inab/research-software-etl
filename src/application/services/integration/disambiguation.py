import requests
import json
import time
import os
import logging
from pathlib import Path
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from jinja2 import Template
from functools import lru_cache
from readability import Document
from bs4 import BeautifulSoup
import tiktoken

from src.application.services.integration.enrich_links import enrich_webpages, enrich_repositories

# -------------------------------
# Configuration
# -------------------------------

API_KEY = os.environ.get("OPENROUTER_API_KEY")
API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "meta-llama/llama-3.3-70b-instruct:free"
REQUESTS_PER_MINUTE = 20
DELAY_BETWEEN_REQUESTS = 60 / REQUESTS_PER_MINUTE
MAX_TOTAL_TOKENS = 130000  # Token cap based on Together.ai model limit

logging.basicConfig(level=logging.INFO)

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
# HTML Cleaning and Chunking
# -------------------------------

def extract_text_from_html(html: str) -> str:
    if not html or not isinstance(html, str):
        logging.warning("No valid HTML string provided to readability.")
        return ""

    try:
        doc = Document(html)
        summary_html = doc.summary()
        soup = BeautifulSoup(summary_html, 'html.parser')
        return soup.get_text(separator='\n', strip=True)
    except Exception as e:
        logging.error(f"Error parsing HTML with readability: {e}")
        return ""


def chunk_text(text: str, max_tokens: int = 8000, model: str = "gpt-4"):
    enc = get_tokenizer(model)
    words = text.split()
    chunks = []
    current_chunk = []
    current_token_count = 0

    for word in words:
        token_len = len(enc.encode(word + " "))
        if current_token_count + token_len > max_tokens:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_token_count = token_len
        else:
            current_chunk.append(word)
            current_token_count += token_len

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks

def clean_and_chunk_html(html: str, max_tokens: int = 8000, model: str = "gpt-4"):
    cleaned_text = extract_text_from_html(html)
    if count_tokens(cleaned_text, model=model) > max_tokens:
        return chunk_text(cleaned_text, max_tokens=max_tokens, model=model)
    else:
        return [cleaned_text]

def split_large_html_entries(entry: dict, max_tokens=8000, model="gpt-4"):
    split_entries = []
    if "readme_content" in entry["data"]:
        chunks = clean_and_chunk_html(entry["data"]["readme_content"], max_tokens=max_tokens, model=model)
        if len(chunks) > 1:
            logging.info(f"Splitting entry {entry['id']} into {len(chunks)} parts.")
            for i, chunk in enumerate(chunks):
                new_entry = entry.copy()
                new_entry["data"] = new_entry["data"].copy()
                new_entry["id"] = f"{entry['id']}_part{i+1}"
                new_entry["data"]["readme_content"] = chunk
                split_entries.append(new_entry)

    if "webpage" in entry["data"]:
        for link in entry["data"]["webpage"]:
            if "content" in link:
                html = link["content"]
                chunks = clean_and_chunk_html(html, max_tokens=max_tokens, model=model)
                if len(chunks) > 1:
                    logging.info(f"Splitting entry {entry['id']} into {len(chunks)} parts.")
                    for a, chunk in enumerate(chunks):
                        new_entry = entry.copy()
                        new_entry["data"] = new_entry["data"].copy()
                        new_entry["id"] = f"{entry['id']}_part{i+a+1}"
                        new_entry["data"]["webpage"] = [{
                            "url": link["url"],
                            "content": chunk
                        }]
                        split_entries.append(new_entry)
    if split_entries:
        logging.info(f"Split entry {entry['id']} into {len(split_entries)} parts.")
        return split_entries
    else:
        return [entry]

def preprocess_entries_for_html_chunking(entries: list):
    result = []
    for entry in entries:
        result.extend(split_large_html_entries(entry))
    return result

# -------------------------------
# Prompt + Chat Message Builder
# -------------------------------

def build_chat_messages_with_disconnected(
    instruction_prompt: str,
    conflict_data: dict,
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

    def chunk_dict_of_lists(d: dict, label: str):
        """Yields tuples of (url, chunk_text) for each content chunk in dict"""
        for url, chunks in d.items():
            for i, chunk in enumerate(chunks):
                text = f"{label} content from {url} (part {i+1}):\n```\n{chunk}\n```"
                yield {"role": "user", "content": text}

    # Add entries: known and disconnected tools
    if conflict_data.get("remaining"):
        for i, chunk in enumerate(chunk_entries(conflict_data["remaining"])):
            messages.append({
                "role": "user",
                "content": f"Part {i+1} — tools known to be the **same software**:\n```json\n{json.dumps(chunk, indent=2, ensure_ascii=False)}\n```"
            })

    if conflict_data.get("disconnected"):
        for i, chunk in enumerate(chunk_entries(conflict_data["disconnected"])):
            messages.append({
                "role": "user",
                "content": f"Part {i+1} — **disconnected tools** to be analyzed:\n```json\n{json.dumps(chunk, indent=2, ensure_ascii=False)}\n```"
            })

    # Add enriched webpage and repository contents
    if "webpage_contents" in conflict_data:
        for chunk in chunk_dict_of_lists(conflict_data["webpage_contents"], "Webpage"):
            messages.append(chunk)

    if "repository_contents" in conflict_data:
        for chunk in chunk_dict_of_lists(conflict_data["repository_contents"], "Repository README"):
            messages.append(chunk)

    # Final instruction
    messages.append({
        "role": "user",
        "content": "All parts have been sent. Please now analyze the entries and provide the output as specified."
    })

    # Token budget check
    total_tokens = estimate_total_tokens(messages, model=model)
    logging.info(f"Total tokens: {total_tokens}")
    if total_tokens > MAX_TOTAL_TOKENS:
        raise ValueError(f"Prompt too long: {total_tokens} tokens. Limit is {MAX_TOTAL_TOKENS}.")

    return messages


# -------------------------------
# Prompt Selection
# -------------------------------

def build_prompt(disconnected, remaining):
    n_disconnected = len(disconnected)
    n_remaining = len(remaining)

    if n_disconnected == 1 and n_remaining == 1:
        logging.info("Using template: disconnected_entries")
        template = PROMPT_TEMPLATES["disconnected_entries"]
    elif n_disconnected > 1 and n_remaining == 0:
        logging.info("Using template: disconnected_entries")
        template = PROMPT_TEMPLATES["disconnected_entries"]
    elif n_disconnected == 1 and n_remaining > 1:
        logging.info("Using template: one_disconnected_several_remaining")
        template = PROMPT_TEMPLATES["one_disconnected_several_remaining"]
    elif n_disconnected > 1 and n_remaining > 1:
        logging.info("Using template: several_disconnected_several_remaining")
        template = PROMPT_TEMPLATES["several_disconnected_several_remaining"]
    else:
        raise ValueError(f"Unsupported combination: {n_disconnected} disconnected, {n_remaining} remaining")

    instruction_prompt = template.render()

    data_dict = {
        "disconnected": disconnected,
        "remaining": remaining
    }

    return build_chat_messages_with_disconnected(instruction_prompt, data_dict)

# -------------------------------
# API Request
# -------------------------------

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def query_openrouter(messages):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.2
    }

    for _ in range(3):
        logging.info(f"Sending request to OpenRouter API: {API_URL} with key {API_KEY[:4]}...")
        response = requests.post(API_URL, headers=headers, json=payload)
        logging.info(f"API response: {response.status_code}")
        if response.status_code == 200:
            try:
                content = response.json()["choices"][0]["message"]["content"].strip()
                if content:
                    return content
            except:
                logging.warning(response.json())
                continue
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")

    logging.warning("API response was empty after 3 attempts.")
    return None


# Process flagged cases
def resolve_conflicts(conflict):
    """ Uses OpenRouter to resolve flagged software conflicts. """

    # Query LLM to check if they are the same
    try: 
        result = query_openrouter(conflict)

        time.sleep(DELAY_BETWEEN_REQUESTS)  # Respect API rate limit
    
    except Exception as e:
        logging.error(f"Error resolving conflict: {e}")
        return None
    

    return result

# -------------------------------
# Conflict Handling
# -------------------------------

def build_full_conflict(conflict, instances_dict, max_tokens=8000, model="gpt-4"):
    """
    Returns a conflict dictionary where:
    - 'disconnected' and 'remaining' contain minimal metadata (with URLs)
    - 'webpage_contents' and 'repository_contents' contain deduplicated content
    """
    from collections import defaultdict

    def enrich_and_collect_content(url_list, enrich_func):
        contents = defaultdict(list)
        seen = set()

        for url in url_list:
            if url in seen or not url:
                continue
            seen.add(url)
            enriched = enrich_func([url])
            if enriched and enriched[0].get("content"):
                chunks = clean_and_chunk_html(enriched[0]["content"], max_tokens=max_tokens, model=model)
                contents[url] = chunks
        return dict(contents)

    new_conflict = {
        "disconnected": [],
        "remaining": [],
        "webpage_contents": {},
        "repository_contents": {}
    }

    all_webpages = set()
    all_repos = set()

    def strip_content_fields(entry):
        entry = entry.copy()
        entry["data"] = entry["data"].copy()
        webpages = entry["data"].get("webpage", [])
        repos = entry["data"].get("repository", [])
        all_webpages.update(webpages)
        for repo in repos:  
            if repo.get('kind') == "github" and "github.com" in repo.get('url', ''):
                all_repos.add(repo.get('url', ''))
            else:
                all_webpages.add(repo.get('url', ''))
        
        entry["data"].pop("readme_content", None)
        return entry

    for entry in conflict["disconnected"]:
        instance_id = entry["id"]
        full_entry = instances_dict[instance_id]
        new_conflict["disconnected"].append(strip_content_fields(full_entry))

    for entry in conflict["remaining"]:
        instance_id = entry["id"]
        full_entry = instances_dict[instance_id]
        new_conflict["remaining"].append(strip_content_fields(full_entry))

    # Enrich and chunk all unique URLs
    new_conflict["webpage_contents"] = enrich_and_collect_content(list(all_webpages), enrich_webpages)
    new_conflict["repository_contents"] = enrich_and_collect_content(list(all_repos), enrich_repositories)

    return new_conflict


def parse_result(result):
    try:
        cleaned = result.replace("```python", "").replace("```json", "").replace("```", "")
        return json.loads(cleaned)
    except Exception as e:
        logging.error(f"Error parsing result: {e}")
        return None

def create_issue(issue):
    with open('data/issues.json', 'a') as f:
        f.write(json.dumps(issue, indent=4))


def log_error(conflict):
    with open('data/error_conflicts.json', 'a') as f:
        f.write(json.dumps(conflict, indent=4))


def log_result(result):
    with open('data/results.json', 'a') as f:
        f.write(json.dumps(result, indent=4))
    logging.info("Result logged")


def write_to_results_file(result, results_file):
    try:
        with open(results_file, "a") as f:
            json.dump(result, f)
            f.write("\n")
    except FileNotFoundError:
        logging.error("Error writing to results file")


def load_solved_conflict_keys(jsonl_path):
    solved_keys = set()
    if not os.path.exists(jsonl_path):
        return solved_keys
    with open(jsonl_path, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    entry = json.loads(line)
                    key = next(iter(entry))
                    solved_keys.add(key)
                except Exception as e:
                    logging.warning(f"Could not parse line: {line[:100]}...\n{e}")
    return solved_keys


def resolve_conflicts(conflict):
    try:
        result = query_openrouter(conflict)
        time.sleep(DELAY_BETWEEN_REQUESTS)
        return result
    except Exception as e:
        logging.error(f"Error resolving conflict: {e}")
        return None


def disambiguate_disconnected_entries(disconnected_entries, instances_dict, grouped_entries, results_file):
    disambiguated_grouped = {}
    results = {}
    count = 0
    solved_conflicts_keys = load_solved_conflict_keys(results_file)

    for key in grouped_entries:
        if key in disconnected_entries:
            if key not in solved_conflicts_keys and count < 180:
                count += 1
                logging.info(f"Processing conflict {count} - {key}")
                try:
                    full_conflict = build_full_conflict(disconnected_entries[key], instances_dict)
                    messages = build_prompt(full_conflict["disconnected"], full_conflict["remaining"])
                    logging.info(f"Sending messages to OpenRouter for conflict {key}")
                    logging.info(f"Number of messages: {len(messages)}")
                    result = resolve_conflicts(messages)
                    parsed = parse_result(result)
                    if parsed:
                        logging.info(f"Result for conflict {key}: {parsed}")
                        results[key] = parsed
                        solved_conflicts_keys.add(key)
                        write_to_results_file({key: parsed}, results_file)
                        if parsed["verdict"] != "Unclear":
                            disambiguated_grouped[key] = {
                                'instances': [[instances_dict[id] for id in group] for group in parsed["groups"]]
                            }
                        else:
                            create_issue(parsed['github_issue'])
                except Exception as e:
                    raise e
                    #logging.error(f"Error processing conflict {key}: {e}")
        else:
            disambiguated_grouped[key] = {'instances': grouped_entries[key]['instances']}

    return disambiguated_grouped, results


if __name__ == "__main__":
    disconnected_entries_file = 'data/disconnected_entries.json'
    instances_dict_file = 'data/instances_dict.json'
    grouped_entries_file = 'data/grouped.json'
    results_file = 'data/results.json'

    disambiguate_disconnected_entries(disconnected_entries_file, instances_dict_file, grouped_entries_file, results_file)