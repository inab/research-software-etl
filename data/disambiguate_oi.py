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

# OpenWebUI API Settings
API_KEY = "sk-50f4598023f64dc89dab58d1a8fc5a35"  # If authentication is required
API_URL = "https://gepeto.bsc.es/api/v1/chat/completions"  # Replace with actual endpoint
MODEL = "llama3.3:latest"  # Check which models are available on the instance

# Rate limit settings (adjust based on institutional policies)
REQUESTS_PER_MINUTE = 20  # Modify if your institution has different limits
DELAY_BETWEEN_REQUESTS = 60 / REQUESTS_PER_MINUTE  # Time delay to respect rate limit


# OpenWebUI API call
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

    formatted_message = template.render(data=data_dict)
    return formatted_message


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def query_openwebui(prompt):
    """Queries OpenWebUI AI to determine if two software tools are the same, with retries."""
    headers = {
        "Content-Type": "application/json"
    }
    if API_KEY:  # If authentication is enabled
        headers["Authorization"] = f"Bearer {API_KEY}"

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
    """ Uses OpenWebUI to resolve flagged software conflicts. """

    # Query LLM to check if they are the same
    result = query_openwebui(conflict)

    time.sleep(DELAY_BETWEEN_REQUESTS)  # Respect API rate limit

    return result


def disambiguate_entries(prompt_message):
    resolved_conflict = resolve_conflicts(prompt_message)
    return resolved_conflict
    