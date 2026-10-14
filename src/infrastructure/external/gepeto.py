from __future__ import annotations

import logging
import time
from typing import Any

import requests
from tenacity import Retrying, stop_after_attempt, wait_exponential


class GepetoClient:
    """Chat-completions client for Gepeto, the BSC LLM provider.

    Gepeto is an Open WebUI instance that exposes an OpenAI-compatible
    ``/api/chat/completions`` endpoint.
    """

    BASE_URL = "https://gepeto.bsc.es/api"

    def __init__(
        self, api_key: str | None = None, timeout: float | None = None
    ) -> None:
        self.api_key = api_key
        # Seconds per HTTP attempt; None waits forever (requests' default).
        self.timeout = timeout

    def query(
        self, messages: Any, model: str, temperature: float = 0.2
    ) -> tuple[str, dict]:
        """
        Send a chat completion request.

        Returns (content, metadata). On an empty or unparseable response, returns
        ("", metadata) rather than raising -- callers treat a missing verdict as
        "no opinion" and fall back to the other model. Transport errors are
        retried (3 attempts) and then raised.

        The metadata is the response's ``usage`` plus timing of the call, for
        monitoring the service: ``latency_s`` (the last HTTP attempt),
        ``total_s`` (every attempt, including retry back-off), ``attempts``,
        ``http_status`` and, when no content came back, ``error``.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        url = f"{self.BASE_URL}/chat/completions"
        logging.info(f"Sending request to Gepeto API: {url}")

        started = time.perf_counter()
        for attempt in Retrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=10),
        ):
            with attempt:
                sent = time.perf_counter()
                response = requests.post(
                    url, json=payload, headers=headers, timeout=self.timeout
                )
        timing = {
            "provider": "gepeto",
            "model": model,
            "http_status": response.status_code,
            "latency_s": round(time.perf_counter() - sent, 3),
            "total_s": round(time.perf_counter() - started, 3),
            "attempts": attempt.retry_state.attempt_number,
        }

        if response.status_code == 200:
            try:
                body = response.json()
                content = body["choices"][0]["message"]["content"].strip()
                meta = {**(body.get("usage") or {}), **timing}
                if content:
                    return content, meta
                timing["error"] = "empty content"
            except Exception:
                logging.warning(response.text[:500])
                timing["error"] = "unparseable response"
        else:
            timing["error"] = response.text[:500]

        logging.warning(
            f"API response was empty: {response.status_code} - {response.text}"
        )
        return "", timing
