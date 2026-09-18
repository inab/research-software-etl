import logging
import json
import re

from infrastructure.external.clients import ExternalClients


def decision_agreement_proxy(
    messages: str, clients: ExternalClients, model_a: str, model_b: str
) -> dict:
    """
    Ask two models the same question and report whether they agree.

    Both opinions come from Gepeto, but from two *different* models (``model_a``
    and ``model_b``) so a genuine disagreement can surface. Returns the shared
    verdict when they agree, or {"verdict": "disagreement"} when they don't --
    which is what escalates the conflict to a curator.
    """
    # model A, via Gepeto
    result_a, meta_a = clients.gepeto.query(messages, model=model_a)
    try:
        result_a = parse_result(result_a)
    except Exception as e:
        logging.warning(f"Parsing error: {e} | Response: {result_a}")
        result_a = {}

    # model B, via Gepeto
    result_b, meta_b = clients.gepeto.query(messages, model=model_b)
    try:
        result_b = parse_result(result_b)
    except Exception:
        result_b = {}

    # agreement
    result_a_verdict = result_a.get("verdict", None)
    result_b_verdict = result_b.get("verdict", None)
    # if both models agree, return the result
    if result_a_verdict == result_b_verdict:
        if result_a_verdict is not None:
            return {
                "verdict": result_a_verdict,
                "model_a": result_a,
                "model_b": result_b,
            }
        # If models agree and are None, human annotation is needed

    else:
        return {
            "verdict": "disagreement",
            "model_a": result_a,
            "model_b": result_b,
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
