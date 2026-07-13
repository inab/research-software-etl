from __future__ import annotations

import logging
from typing import Any

import requests


class HuggingFaceClient:
    """Client for the HuggingFace inference and router APIs."""

    INFERENCE_URL = "https://api-inference.huggingface.co/models"
    ROUTER_URL = "https://router.huggingface.co"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    def query_chat(self, messages: Any, model: str, provider: str) -> tuple[str, dict]:
        """
        Chat completion via the router API, served by `provider` (e.g. "together").

        Returns (content, usage_metadata), or ("", {}) if the response is empty.
        Raises on a parse failure so the caller's retry/backoff can see it.
        """
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": model, "messages": messages}

        url = f"{self.ROUTER_URL}/{provider}/v1/chat/completions"
        logging.info(f"Sending request to Hugging Face router API: {url}")

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        if response.status_code == 200:
            try:
                body = response.json()
                content = body["choices"][0]["message"]["content"].strip()
                meta = body.get("usage", {})
                meta["provider"] = provider
                if content:
                    return content, meta
            except Exception as e:
                logging.warning(f"Parsing error: {e} | Response: {response.json()}")
                raise

        logging.warning("API response was empty")
        return "", {}

    def query_inference(self, messages: Any, model: str) -> str | None:
        """Text generation via the classic inference API."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": messages,
            "parameters": {
                "temperature": 0.2,
                "top_p": 0.95,
                "max_new_tokens": 512,
                "return_full_text": False,
            },
        }

        url = f"{self.INFERENCE_URL}/{model}"
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            try:
                return response.json()[0]["generated_text"].strip()
            except Exception as e:
                logging.warning(f"Parsing error: {e} | Response: {response.json()}")

        return None
