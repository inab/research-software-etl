import logging
import json
import re

from infrastructure.external.clients import ExternalClients

# Models the two independent opinions come from. They must disagree for a
# conflict to escalate to a human, so they are deliberately different families.
LLAMA_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
LLAMA_PROVIDER = "together"
MIXTRAL_MODEL = "mistralai/mixtral-8x7b-instruct"


def decision_agreement_proxy(messages: str, clients: ExternalClients) -> dict:
    """
    Ask two models the same question and report whether they agree.

    Returns the shared verdict when they agree, or {"verdict": "disagreement"}
    when they don't -- which is what escalates the conflict to a curator.
    """
    # model 1: Llama, via HuggingFace
    result_llama_4, meta_llama_4 = clients.huggingface.query_chat(
        messages, model=LLAMA_MODEL, provider=LLAMA_PROVIDER
    )
    try:
        result_llama_4 = parse_result(result_llama_4)
    except Exception as e:
        logging.warning(f"Parsing error: {e} | Response: {result_llama_4}")
        result_llama_4 = {}

    # model 2: Mixtral 8x7B, via OpenRouter
    result_mixtral, meta_mixtral = clients.openrouter.query(messages, model=MIXTRAL_MODEL)
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
            return {
                'verdict': result_llama_4_verdict,
                'llama_4': result_llama_4,
                'mixtral': result_mixtral
            }
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