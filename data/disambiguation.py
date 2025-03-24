import requests
import json
import time
import ast
from tenacity import retry, stop_after_attempt, wait_exponential
from jinja2 import Template
import prompts.disconnected_entries
import prompts.one_disconnected_several_remaining
import prompts.several_disconnected_several_remaining
from prompts.schema import schema

from enrich_links import enrich_webpages, enrich_repositories


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
        prompt = prompts.disconnected_entries.prompt
    
    elif n_disconnected > 1 and n_remaining == 0:
        print("Using template `disconnected_entries`")
        prompt = prompts.disconnected_entries.prompt

    elif n_disconnected == 1 and n_remaining > 1:
        print("Using template `one_disconnected_several_remaining`")
        prompt = prompts.one_disconnected_several_remaining.prompt

    elif n_disconnected > 1 and n_remaining > 1:
        print("Using template `several_disconnected_several_remaining`")
        prompt = prompts.several_disconnected_several_remaining.prompt

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
    result = query_openrouter(conflict)

    time.sleep(DELAY_BETWEEN_REQUESTS)  # Respect API rate limit

    return result


def check_if_conflictive(key):
    """Check if a given key is in the disconnected entries list."""
    return key in disconnected_entries


def build_full_conflict(conflict):
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
    result = result.replace("```python", "").replace("```json", "").replace("```", "")
    return json.loads(result)


def create_issue(issue):
    """Save detected conflicts as issues."""
    with open('data/issues.json', 'a') as f:
        f.write(json.dumps(issue, indent=4))


def log_error(conflict):
    """Log errors when processing conflicts."""
    with open('data/error_conflicts.json', 'a') as f:
        f.write(json.dumps(conflict, indent=4))


def disambiguate_entries(disconnected_entries_file, instances_dict_file, grouped_entries_file):
    with open(disconnected_entries_file, 'r') as f:
        disconnected_entries = json.load(f)

    with open(instances_dict_file, 'r') as f:
        instances_dict = json.load(f)
    
    with open(grouped_entries_file, 'r') as f:
        grouped_entries = json.load(f)

    disambiguated_grouped = {}
    results = {}
    count = 0
    
    for key in disconnected_entries:
        if count >= 199:  # Stop after 199 iterations
            break

        if check_if_conflictive(key):
            try:
                full_conflict = build_full_conflict(disconnected_entries[key])
                prompt = build_prompt(full_conflict["disconnected"], full_conflict["remaining"])
                result = parse_result(resolve_conflicts(prompt))
                log_result(result)
                results.append(result)
                if result["verdict"] != "Unclear":
                    disambiguated_grouped[key] = {'instances': [[instances_dict[id] for id in group] for group in result["groups"]]}
                else:
                    create_issue(result['github_issue'])
            except Exception:
                log_error(full_conflict)
        else:
            disambiguated_grouped[key] = {'instances': grouped_entries[key]['instances']}
    
    with open('data/results.json', 'w') as f:
        f.write(json.dumps(results))

    with open('data/disambiguated_grouped.json', 'w') as f:
        f.write(json.dumps(disambiguated_grouped))

    return 

def log_result(result):
    '''writes to file without deleting previous results'''
    with open('data/results.json', 'a') as f:
        f.write(json.dumps(result, indent=4))
    print("Result logged")



if __name__ == "__main__":

    disconnected_entries_file = 'data/disconnected_entries.json'
    instances_dict_file = 'data/instances_dict.json'
    grouped_entries_file = 'data/grouped.json'

    disambiguate_entries(disconnected_entries_file, instances_dict_file, grouped_entries_file)

    

    
