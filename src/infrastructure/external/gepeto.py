from __future__ import annotations

import logging
from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential


class GepetoClient:
    """Chat-completions client for Gepeto, the BSC LLM provider.

    Gepeto is an Open WebUI instance that exposes an OpenAI-compatible
    ``/api/chat/completions`` endpoint.
    """

    BASE_URL = "https://gepeto.bsc.es/api"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def query(self, messages: Any, model: str) -> tuple[str, dict]:
        """
        Send a chat completion request.

        Returns (content, usage_metadata). On an empty or unparseable response,
        returns ("", {}) rather than raising -- callers treat a missing verdict
        as "no opinion" and fall back to the other model.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
        }

        url = f"{self.BASE_URL}/chat/completions"
        logging.info(f"Sending request to Gepeto API: {url}")

        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 200:
            try:
                body = response.json()
                content = body["choices"][0]["message"]["content"].strip()
                meta = body.get("usage", {})
                meta["provider"] = "gepeto"
                if content:
                    return content, meta
            except Exception:
                logging.warning(response.json())

        logging.warning(
            f"API response was empty: {response.status_code} - {response.text}"
        )
        return "", {}
