import requests
import json
import re
import os
import logging
from pathlib import Path
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential
from jinja2 import Template
from functools import lru_cache
import tiktoken
import datetime

from src.application.services.integration.enrich_links import enrich_link
from src.application.services.integration.github_issue_helpers import generate_github_issue, create_issue, generate_context
from src.domain.models.software_instance.multitype_instance import multitype_instance

# -------------------------------
# Configuration
# -------------------------------

# OpenRouter - https://openrouter.ai
OR_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OR_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "meta-llama/llama-3.3-70b-instruct:free"
REQUESTS_PER_MINUTE = 20
DELAY_BETWEEN_REQUESTS = 60 / REQUESTS_PER_MINUTE
MAX_TOTAL_TOKENS = 130000  


# HuggingFace - https://huggingface.co
HF_API_URL = "https://api-inference.huggingface.co/models" 
HF_API_KEY = os.environ.get("HUGGINGFACE_API_KEY")




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
# Chunking big text
# -------------------------------
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
def query_openrouter(messages, model):
    headers = {
        "Authorization": f"Bearer {OR_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2
    }

    logging.info(f"Sending request to OpenRouter API: {OR_API_URL} with key {OR_API_KEY[:4]}...")
    
    response = requests.post(OR_API_URL, json=payload, headers=headers )
    
    if response.status_code == 200:
        try:
            # main answer 
            content = response.json()["choices"][0]["message"]["content"].strip()
            # metadata
            meta = response.json().get("usage", {})
            meta['provider'] = response.json().get("provider", "")
            if content:
                return content, meta
        except:
            logging.warning(response.json())
    
    logging.warning(f"API response was empty: {response.status_code} - {response.text}")
    return '', {}




#@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def query_huggingface_new(messages, model, provider):
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
    }
    payload = {
        "model": model,
        "messages": messages,
    }
     
    URL = f"https://router.huggingface.co/{provider}/v1/chat/completions"
    logging.info(f"Sending request to Hugging Face Inference API: {URL} with key {HF_API_KEY[:4]}...")
    
    response = requests.post(URL, headers=headers, json=payload)
    logging.info(f"API response: {response}")
    if response.status_code == 200:
        try:
            # main answer 
            content = response.json()["choices"][0]["message"]["content"].strip()
            # metadata
            meta = response.json().get("usage", {})
            meta['provider'] = provider
            if content:
                return content, meta
           
        except Exception as e:
            logging.warning(f"Parsing error: {e} | Response: {response.json()}")
        
    logging.warning("API response was empty after 3 attempts.")
    return '', {}

def query_huggingface(messages, model):
    headers = {
        "Authorization": f"Bearer {HF_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = { 
        "inputs": messages,
        "parameters": {
            "temperature": 0.2,
            "top_p": 0.95,
            "max_new_tokens": 512,
            "return_full_text": False
        }
    }
     
    URL = f"{HF_API_URL}/{model}"
    logging.info(f"Sending request to Hugging Face Inference API: {URL} with key {HF_API_KEY[:4]}...")
    
    response = requests.post(URL, headers=headers, json=payload)
    logging.info(f"API response: {response.json()}")
    if response.status_code == 200:
        try:
            print(f"Whole response: {response.json()}")
            output_text = response.json()[0]["generated_text"].strip()
            # TODO: extract metadata
            return output_text, {}  
        except Exception as e:
            logging.warning(f"Parsing error: {e} | Response: {response.json()}")
        
    logging.warning("API response was empty after 3 attempts.")
    return None


# -------------------------------
# Conflict Handling
# -------------------------------

async def build_full_conflict(conflict, max_tokens=8000, model="gpt-4"):
    """
    Returns a conflict dictionary where:
    - 'disconnected' and 'remaining' contain minimal metadata (with URLs)
    - 'webpage_contents' and 'repository_contents' contain deduplicated content
    """

    async def enrich_and_collect_content(url_list):
        contents = {}
        seen = set()

        for url in url_list:
            if url in seen or not url:
                continue
            seen.add(url)

            enriched = await enrich_link(url)

            contents[url] = {}

            if enriched and enriched.get("content"):
                chunks = chunk_text(enriched["content"], max_tokens=max_tokens, model=model)
                contents[url]["Content"]  = chunks

            if enriched and enriched.get("readme_content"):
                contents[url]["README content"] = chunk_text(enriched.get("readme_content"), max_tokens=max_tokens, model=model)
            
            if enriched and enriched.get("repo_metadata"):
                contents[url]['Repository metadata'] = enriched["repo_metadata"]
            
            if enriched and enriched.get("project_metadata"):
                contents[url]["Project metadata"] = enriched["project_metadata"]

        return dict(contents)


    new_conflict = {
        "disconnected": [],
        "remaining": [],
        "webpage_contents": {},
    }

    all_webpages = set()
    all_repos = set()

    def strip_content_fields(entry):
        entry = entry.copy()
        webpages = entry.get("webpage", [])
        repos = entry.get("repository", [])
        all_webpages.update(webpages)
        for repo in repos:  
            if repo.get('kind') == "github" and "github.com" in repo.get('url', ''):
                all_repos.add(repo.get('url', ''))
            elif repo.get('kind') == "bitbucket" and "bitbucket.com" in repo.get('url', ''):
                all_repos.add(repo.get('url', ''))
            elif repo.get('kind') == "gitlab" and "gitlab.com" in repo.get('url', ''):
                all_repos.add(repo.get('url', ''))
            else:
                all_webpages.add(repo.get('url', ''))
            
        return entry

    for entry in conflict["disconnected"]:
        new_conflict["disconnected"].append(strip_content_fields(entry))

    for entry in conflict["remaining"]:
        new_conflict["remaining"].append(strip_content_fields(entry))

    # Enrich and chunk all unique URLs
    repos_and_webpages = all_webpages.union(all_repos)
    all_links = set(repos_and_webpages)
    new_conflict["webpage_contents"] = await enrich_and_collect_content(list(all_links))

    return new_conflict


def parse_result(text):
    """
    Extracts and parses a JSON object from either a Markdown-style code block or raw inline JSON.

    Args:
        text (str): Input text containing the dictionary.

    Returns:
        dict: Parsed JSON object as a Python dictionary.

    Raises:
        ValueError: If no valid JSON is found or if JSON parsing fails.
    """

    # Try to extract from code block first
    match = re.search(r"```(?:json|python)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        # Fallback: try to find a top-level JSON object in plain text
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            logging.warning("No JSON object found in input.")
            return {}

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logging.warning(f"Failed to parse JSON: {e}")
        return {}



def log_error(conflict):
    with open('data/error_conflicts.json', 'a') as f:
        f.write(json.dumps(conflict, indent=4))


def log_result(result):
    with open('data/results.json', 'a') as f:
        f.write(json.dumps(result, indent=4))
    logging.info("Result logged")


def write_to_results_file(result, results_file):
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(results_file), exist_ok=True)
        
        with open(results_file, "a") as f:
            json.dump(result, f)
            f.write("\n")
    except Exception as e:
        logging.error(f"Error writing to results file: {e}")

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


def decision_agreement_proxy(messages: str) -> str:
    """
    This function takes a message as input and returns the agreement of the models.
    It uses the `decision_agreement` function from the `decision_agreement` module.
    """
    # model 1: Llama 4 Scout
    model = "meta-llama/Llama-4-Scout-17B-16E-Instruct"
    provider = "together"
    result_llama_4, meta_llama_4 = query_huggingface_new(messages, model=model, provider=provider)
    try:
        result_llama_4 = parse_result(result_llama_4)
    except Exception as e:
        result_llama_4 = {}

    # model 2: Mixtral 8x7B
    model = "mistralai/mixtral-8x7b-instruct"
    result_mixtral, meta_mixtral = query_openrouter(messages, model=model)
    try:
        result_mixtral = parse_result(result_mixtral)
    except Exception as e:
        result_mixtral = {}
    
    # agreement
    result_llama_4_verdict = result_llama_4.get("verdict", None)
    result_mixtral_verdict = result_mixtral.get("verdict", None)
    # if both models agree, return the result
    if result_llama_4_verdict == result_mixtral_verdict:
        if result_llama_4_verdict != None:
            return result_llama_4
        # If models agree and are None, human annotation is needed
        
    else:
        return {
            "verdict": "disagreement",
            "llama_4": result_llama_4,
            "mixtral": result_mixtral,
        }
    

def convert_to_multi_type_instance(instance_data_dict):
    if instance_data_dict['type']:
        instance_data_dict['type'] = [instance_data_dict['type']]
    else:
        instance_data_dict['type'] = []
    
    instance_data_dict['other_names'] = []

    return multitype_instance(**instance_data_dict)


def merge_instances(instances):
    merged_instances = instances[0]
    for instance in instances[1:]:
        merged_instances = merged_instances.merge(instance)   

    return merged_instances 


def merge_remaining(entries):
    entries_remaining_dict = {}
    for entry in entries:
        id = entry["_id"]
        metadata = entry["data"]
        entries_remaining_dict[id] = convert_to_multi_type_instance(metadata)
    
    print('Instances in group converted to multitype_instance.')
    ids_remaining = [entry["_id"] for entry in entries]
    # merge entries
    print(f"Merging {len(entries_remaining_dict)} entries in group...")
    instances = [entries_remaining_dict[id] for id in ids_remaining]
    merged_instances = merge_instances(instances)

    # convert to dictionary again
    entry_remaining_merged = merged_instances.model_dump()

    return entry_remaining_merged

def build_pairs(full_conflict, key, more_than_two_pairs):
    """
    Function to build pairs of disconnected and remaining entries.
    It checks the number of entries in each group and handles them accordingly.
    - If there are no disconnected entries, it skips the conflict.
    - If there are more than two disconnected entries, it creates several pairs.
    - If there are more than two remaining entries, it merges them into one entry.
    """
    pairs = []

    disconnected = full_conflict.get("disconnected", [])
    remaining = full_conflict.get("remaining", [])

    if len(disconnected) == 0:
        # No conflict to resolve
        logging.info(f"Conflict {key} has no disconnected entries. Skipping.")
        return pairs, more_than_two_pairs

    elif len(disconnected) > 1:
        more_than_two_pairs += 1

        if len(remaining) == 0:
            if len(disconnected) == 2:
                # Treat first as remaining, second as disconnected
                pair = {
                    "remaining": [disconnected[0]],
                    "disconnected": disconnected[1]
                }
                pairs.append(pair)
            else:
                # No remaining, and more than two disconnected – pair disconnected entries among themselves
                for i in range(1, len(disconnected)):
                    pair = {
                        "remaining": [disconnected[0]],  # use first as pseudo-"remaining"
                        "disconnected": disconnected[i]
                    }
                    pairs.append(pair)
            return pairs, more_than_two_pairs

        elif len(remaining) == 1:
            # Pair each disconnected with the single remaining
            for disc in disconnected:
                pair = {
                    "remaining": [remaining[0]],
                    "disconnected": disc
                }
                pairs.append(pair)
            return pairs, more_than_two_pairs

        elif len(remaining) > 1:
            # Merge remaining entries into one, and pair each disconnected with the merged remaining
            merged = merge_remaining(remaining)
            for disc in disconnected:
                pair = {
                    "remaining": [merged],
                    "disconnected": disc
                }
                pairs.append(pair)
            return pairs, more_than_two_pairs

    else:
        # Only one disconnected entry
        if len(remaining) == 0:
            # Not enough context to make a pair
            logging.info(f"Conflict {key} has only one disconnected and no remaining entries. Skipping.")
            return pairs, more_than_two_pairs

        elif len(remaining) == 1:
            # Simple pair
            pairs.append(full_conflict)
            return pairs, more_than_two_pairs

        elif len(remaining) > 1:
            # Merge remaining entries and create one pair
            full_conflict['remaining'] = [merge_remaining(remaining)]
            pairs.append(full_conflict)
            return pairs, more_than_two_pairs

    return pairs, more_than_two_pairs




def build_instances_keys_dict(data):
    """Create a mapping of instance IDs to their respective instance data."""
    instances_keys = {}
    for key, value in data.items():
        instances = value.get("instances", [])
        for instance in instances:
            instances_keys[instance["_id"]] = instance
    return instances_keys


def replace_with_full_entries(conflict, instances_dict):
    new_conflict = {
        "disconnected": [],
        "remaining": [],
    }
    for entry in conflict['disconnected']:
        entry_id = entry["id"]
        new_conflict['disconnected'].append(instances_dict.get(entry_id))

    for entry in conflict['remaining']:
        entry_id = entry["id"]
        new_conflict['remaining'].append(instances_dict.get(entry_id))
    
    return new_conflict

def filter_relevant_fields(conflict):
    """
    Filter the relevant fields from the conflict dictionary.
    """
    filtered_conflict = {
        "disconnected": [],
        "remaining": []
    }

    for entry in conflict["disconnected"]:
        filtered_entry = {
            "id": entry["id"],
            "name": entry["name"],
            "description": entry["description"],
            "repository": entry["repository"],
            "webpage": entry["webpage"],
            "source": entry["source"],
            "license": entry["license"],
            "authors": entry["authors"],
            "publication": entry["publication"],
            "documentation": entry["documentation"],
        }
        filtered_conflict["disconnected"].append(filtered_entry)

    for entry in conflict["remaining"]:
        filtered_entry = {
            "id": entry["id"],
            "name": entry["name"],
            "description": entry["description"],
            "repository": entry["repository"],
            "webpage": entry["webpage"],
            "source": entry["source"],
            "license": entry["license"],
            "authors": entry["authors"],
            "publication": entry["publication"],
            "documentation": entry["documentation"],
        }
        filtered_conflict["remaining"].append(filtered_entry)

    return filtered_conflict



def build_disambiguated_record(block_id, block, pair_results, model_name="auto:agreement-proxy-v"):
    """
    Given the results of pairwise disambiguation, build a complete
    record for disambiguated_blocks.json.
    """
    merged_ids = [entry["id"] for entry in block.get("remaining", [])]
    unmerged_ids = []
    confidence_scores = {}

    for res in pair_results:
        confidence_scores[res["disconnected_id"]] = res["confidence"]
        if res["same_as_remaining"]:
            merged_ids.append(res["disconnected_id"])
        else:
            unmerged_ids.append(res["disconnected_id"])

    record = {
        "resolution": "merged" if not unmerged_ids else "partial",
        "merged_entries": merged_ids,
        "unmerged_entries": unmerged_ids,
        "source": model_name,
        "confidence_scores": confidence_scores,
        "timestamp": datetime.utcnow().isoformat(),
        "notes": None
    }

    return {block_id: record}



def process_conflict(key, conflict, instances_dict, model_name="auto:mistral-7b"):
    """
    Process a single conflict block: build pairs, disambiguate them, and return
    a disambiguated_blocks record for this block.
    """

    # Replace summary info with full entries
    conflict = replace_with_full_entries(conflict, instances_dict)

    # Build disambiguation pairs
    conflict_pairs, _ = build_pairs(conflict, key, more_than_two_pairs=0)

    pair_results = []

    for conflict_pair in conflict_pairs:
        # Prepare minimal, enriched entry for disambiguation
        full_conflict = filter_relevant_fields(conflict_pair)
        full_conflict = build_full_conflict(full_conflict)

        # Generate prompt and run model
        messages = build_prompt(full_conflict["disconnected"], full_conflict["remaining"])
        result = decision_agreement_proxy(messages)

        if result.get("verdict") != "disagreement":
            pair_results.append({
                "disconnected_id": full_conflict["disconnected"]["id"],
                "same_as_remaining": result["verdict"] == "same",
                "confidence": result.get("confidence", 1.0)
            })
        else:
            # Human fallback
            context = generate_context(key, full_conflict)
            body = generate_github_issue(context, 'github_issue.jinja2')
            title = f"Manual resolution needed for {key}"
            labels = ['conflict']
            create_issue(title, body, labels)

    # Build final record
    return build_disambiguated_record(key, conflict, pair_results, model_name)


def build_no_conflict_record(block_id, block, source="auto:no_disagreement"):
    """
    Generate a disambiguated_blocks record for a block with no disconnected entries.
    This assumes all entries are already grouped (e.g., they share a repo or author).
    """
    merged_ids = [entry["id"] for entry in block.get("instances", [])]

    return {
        block_id: {
            "resolution": "no_conflict",
            "merged_entries": merged_ids,
            "unmerged_entries": [],
            "source": source,
            "confidence_scores": {},
            "timestamp": datetime.utcnow().isoformat(),
            "notes": "All entries grouped heuristically or by shared metadata. No disambiguation needed."
        }
    }

# ----------------- FIRST ROUND OF DISAMBIGUATION -----------------
def disambiguate_blocks(conflict_blocks, blocks, disambiguated_blocks):
    '''
    Disambiguated blocks can be empty at the beginning.
    The function will fill it with the disambiguated entries.
    '''
    instances_dict = build_instances_keys_dict(blocks)
    solved_conflicts_keys = load_solved_conflict_keys(disambiguated_blocks)

    for key in blocks:
        if key in conflict_blocks:
            if key not in solved_conflicts_keys:
                try:
                    record = process_conflict(key, conflict_blocks[key], instances_dict)
                    disambiguated_blocks.update(record)
                except Exception as e:
                    logging.error(f"Error processing conflict {key}: {e}")
                
        else:
            record = build_no_conflict_record(key, blocks[key])
            disambiguated_blocks.update(record)

    return disambiguated_blocks

def generate_secondary_conflicts(disambiguated_blocks, threshold=0.85):
    """
    Create new conflict blocks from unresolved entries in disambiguated_blocks.
    """
    secondary_blocks = {}
    secondary_counter = 0

    for parent_id, record in disambiguated_blocks.items():
        unmerged = record.get("unmerged_entries", [])
        if len(unmerged) > 1:
            for i in range(1, len(unmerged)):
                secondary_counter += 1
                new_id = f"{parent_id}_secondary_{secondary_counter}"
                secondary_blocks[new_id] = {
                    "remaining": [{"id": unmerged[0]}],  # use first as reference
                    "disconnected": [{"id": unmerged[i]}],
                    "parent_block_id": parent_id,
                    "generated_at": datetime.utcnow().isoformat()
                }

    return secondary_blocks


def run_second_round(conflict_blocks_path, disambiguated_blocks_path, blocks, disambiguate_blocks_func):
    """
    Loads existing disambiguation results and conflict blocks,
    generates second-round conflicts, and runs disambiguation again.
    """
    # Load files
    with open(disambiguated_blocks_path, "r") as f:
        disambiguated_blocks = json.load(f)

    with open(conflict_blocks_path, "r") as f:
        conflict_blocks = json.load(f)

    # Generate secondary conflict blocks
    secondary_blocks = generate_secondary_conflicts(disambiguated_blocks)

    if not secondary_blocks:
        print("No secondary conflicts to process.")
        return disambiguated_blocks

    # Update conflict_blocks.json with secondary round blocks
    conflict_blocks.update(secondary_blocks)

    with open(conflict_blocks_path, "w") as f:
        json.dump(conflict_blocks, f, indent=2)

    print(f"🔁 {len(secondary_blocks)} secondary conflict blocks generated and added.")

    # Re-run disambiguation on new conflicts
    updated_disambiguated_blocks = disambiguate_blocks_func(conflict_blocks, blocks, disambiguated_blocks)

    # Save updated disambiguated_blocks.json
    with open(disambiguated_blocks_path, "w") as f:
        json.dump(updated_disambiguated_blocks, f, indent=2)

    print("✅ Second round of disambiguation completed.")
    return updated_disambiguated_blocks


if __name__ == "__main__":
    
    disconnected_entries_file = 'data/disconnected_entries.json'
    instances_dict_file = 'data/instances_dict.json'
    grouped_entries_file = 'data/grouped.json'
    disambiguated_blocks_file = 'data/disambiguated_blocks.json'

    # 1. Load input data
    with open(grouped_entries_file, 'r') as f:
        blocks = json.load(f)

    with open(disconnected_entries_file, 'r') as f:
        conflict_blocks = json.load(f)

    with open(instances_dict_file, 'r') as f:
        instances_dict = json.load(f)

    # 2. Run first round of disambiguation
    disambiguated_blocks = {}

    disambiguated_blocks = disambiguate_blocks(
        conflict_blocks=conflict_blocks,
        blocks=blocks,
        disambiguated_blocks=disambiguated_blocks
    )

    # 3. Save disambiguated_blocks after first round
    with open(disambiguated_blocks_file, 'w') as f:
        json.dump(disambiguated_blocks, f, indent=2)

    # 4. Repeat second-round disambiguation until everything is resolved
    while True:
        # Run a second (or N-th) round
        disambiguated_blocks = run_second_round(
            conflict_blocks_path=disconnected_entries_file,
            disambiguated_blocks_path=disambiguated_blocks_file,
            blocks=blocks,
            disambiguate_blocks_func=disambiguate_blocks
        )

        # Reload conflict_blocks to see what's left
        with open(disconnected_entries_file, 'r') as f:
            conflict_blocks = json.load(f)

        unresolved_keys = [k for k in conflict_blocks if k not in disambiguated_blocks]

        if not unresolved_keys:
            print("🎉 All conflicts resolved.")
            break
        else:
            print(f"🔁 {len(unresolved_keys)} unresolved blocks remain. Continuing...")