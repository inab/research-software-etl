import requests
import json
import time
import os
from tenacity import retry, stop_after_attempt, wait_exponential
from jinja2 import Template
import src.application.services.integration.prompts.disconnected_entries as disconnected_entries
import src.application.services.integration.prompts.one_disconnected_several_remaining as one_disconnected_several_remaining
import src.application.services.integration.prompts.several_disconnected_several_remaining as several_disconnected_several_remaining

from src.application.services.integration.enrich_links import enrich_webpages, enrich_repositories


# OpenRouter API Settings
API_KEY = "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"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
#MODEL = "deepseek-ai/deepseek-llm-67b-chat"  # Best available model
MODEL = "deepseek/deepseek-r1-distill-llama-70b:free"

# Rate limit settings
REQUESTS_PER_MINUTE = 20  # OpenRouter free-tier limit
DELAY_BETWEEN_REQUESTS = 60 / REQUESTS_PER_MINUTE  # Time delay to respect rate limit


# OpenRouter API call

def build_prompt(disconnected, remaining):
    n_disconnected = len(disconnected)
    n_remaining = len(remaining)

    if n_disconnected == 1 and n_remaining == 1:
        print("Using template `disconnected_entries`")
        prompt = disconnected_entries.prompt
    
    elif n_disconnected > 1 and n_remaining == 0:
        print("Using template `disconnected_entries`")
        prompt = disconnected_entries.prompt

    elif n_disconnected == 1 and n_remaining > 1:
        print("Using template `one_disconnected_several_remaining`")
        prompt = one_disconnected_several_remaining.prompt

    elif n_disconnected > 1 and n_remaining > 1:
        print("Using template `several_disconnected_several_remaining`")
        prompt = several_disconnected_several_remaining.prompt

    template = Template(prompt) 
    data_dict = {
        "disconnected": disconnected,
        "remaining": remaining
    }


    # print(data_dict)
    formatted_message = template.render(data=data_dict)
    return formatted_message



@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def query_openrouter(prompt):
    """Queries OpenRouter AI to determine if two software tools are the same, with retries."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,  # Lower temp for more deterministic responses
    }

    for _ in range(3):  # Retry up to 3 times if response content is empty
        response = requests.post(API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            try:
                content = response.json()["choices"][0]["message"]["content"].strip()
                if content:  # Check if content is not empty
                    return content
            except (KeyError, IndexError):
                pass  # Continue retrying if parsing fails
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")
    
    print("API response was empty after 3 attempts.")
    return None


# Process flagged cases
def resolve_conflicts(conflict):
    """ Uses OpenRouter to resolve flagged software conflicts. """

    # Query LLM to check if they are the same
    try: 
        result = query_openrouter(conflict)

        time.sleep(DELAY_BETWEEN_REQUESTS)  # Respect API rate limit
    
    except Exception as e:
        print(f"Error resolving conflict: {e}")
        return None
    

    return result


def check_if_conflictive(key, disconnected_entries):
    """Check if a given key is in the disconnected entries list."""
    return key in disconnected_entries


def build_full_conflict(conflict, instances_dict):
    """Enrich conflict data by fetching full instance details."""
    new_conflict = {"disconnected": [], "remaining": []}
    for instance in conflict['disconnected']:
        instance_id = instance["id"]
        full_instance = instances_dict[instance_id]
        full_instance['data']['webpage'] = enrich_webpages(full_instance['data'].get('webpage', []))
        full_instance['data']['repository'] = enrich_repositories(full_instance['data'].get('repository', []))
        new_conflict["disconnected"].append(full_instance)

    for instance in conflict['remaining']:
        instance_id = instance["id"]
        full_instance = instances_dict[instance_id]
        full_instance['data']['webpage'] = enrich_webpages(full_instance['data'].get('webpage', []))
        full_instance['data']['repository'] = enrich_repositories(full_instance['data'].get('repository', []))
        new_conflict["remaining"].append(full_instance)

    return new_conflict


def parse_result(result):
    """Parse a JSON-formatted string result, removing potential formatting issues."""
    try:
        result = result.replace("```python", "").replace("```json", "").replace("```", "")
    except Exception as e:
        print(f"Error parsing result: {e}")
        print("OpenRouter API response probably emoty. Limit probably reached.")
        return None
    return json.loads(result)


def create_issue(issue):
    """Save detected conflicts as issues."""
    with open('data/issues.json', 'a') as f:
        f.write(json.dumps(issue, indent=4))


def log_error(conflict):
    """Log errors when processing conflicts."""
    with open('data/error_conflicts.json', 'a') as f:
        f.write(json.dumps(conflict, indent=4))


def write_to_results_file(result, results_file):
    """Write the result to a file."""
    print("Writing to results file")
    try:
        with open(results_file, "a") as f:
            json.dump(result, f)
            f.write("\n")

    except FileNotFoundError:
        print("Error writing to results file")

def load_solved_conflict_keys(jsonl_path):
    solved_keys = set()
    
    if not os.path.exists(jsonl_path):
        return solved_keys  # File doesn't exist yet, return empty set

    with open(jsonl_path, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    entry = json.loads(line)
                    key = next(iter(entry))  # top-level key
                    solved_keys.add(key)
                except Exception as e:
                    print(f"Warning: Couldn't parse line:\n{line[:100]}...\n{e}")
    
    return solved_keys


def disambiguate_disconnected_entries(disconnected_entries, instances_dict, grouped_entries, results_file):
    
    disambiguated_grouped = {}
    results = {}
    count = 0

    solved_conflicts_keys = set()
    solved_conflicts_keys = load_solved_conflict_keys(results_file) 
    
    
    for key in grouped_entries:

        # if conflictive, resolve
        if key in disconnected_entries:
            # if the conflict has not been solved yet and we have not reached the limit of 200 conflicts (OpenRouter API limit)
            if key not in solved_conflicts_keys and count < 200:
                count += 1
                print(f"Processing conflict {count}")
                try:
                    full_conflict = build_full_conflict(disconnected_entries[key], instances_dict)
                    print("Full conflict built")
                    prompt = build_prompt(full_conflict["disconnected"], full_conflict["remaining"])
                    print("Prompt built")
                    inference = resolve_conflicts(prompt)
                    result = parse_result(inference)
                    print("Result obtained")
                    log_result(result)
                    if result:
                        results[key] = result
                        solved_conflicts_keys.add(key)
                        write_to_results_file({key: result}, results_file)
                        if result["verdict"] != "Unclear":
                            disambiguated_grouped[key] = {'instances': [[instances_dict[id] for id in group] for group in result["groups"]]}
                        else:
                            create_issue(result['github_issue'])
                            
                except Exception as e:
                    print(f"Error processing conflict: {e}")

        # if not conflictive, keep as is
        else:
            disambiguated_grouped[key] = {'instances': grouped_entries[key]['instances']}
    

    return disambiguated_grouped, results



def log_result(result):
    '''writes to file without deleting previous results'''
    with open('data/results.json', 'a') as f:
        f.write(json.dumps(result, indent=4))
    print("Result logged")



if __name__ == "__main__":

    disconnected_entries_file = 'data/disconnected_entries.json'
    instances_dict_file = 'data/instances_dict.json'
    grouped_entries_file = 'data/grouped.json'
    results_file = 'data/results.json'

    disambiguate_disconnected_entries(disconnected_entries_file, instances_dict_file, grouped_entries_file, results_file)

    

    
