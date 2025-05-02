import logging
import requests
import json
import re
from tenacity import retry, stop_after_attempt, wait_exponential

from src.application.services.integration.disambiguation.config import (
    OR_API_URL,
    OR_API_KEY,
    HF_API_URL,
    HF_API_KEY,
)


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


def decision_agreement_proxy(messages: str) -> str:
    """
    This function takes a message as input and returns the agreement of the models.
    It uses the `decision_agreement` function from the `decision_agreement` module.
    """
    print("Real Decision agreement proxy called")
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