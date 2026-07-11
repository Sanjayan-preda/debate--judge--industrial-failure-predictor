"""
Low-level API client for OpenAI-compatible chat completions.
Used for both the AMD endpoint and Fireworks AI.
"""

import json
import random
import time
from typing import Optional

import requests


class ApiCallResult:
    """Holds the response text and token usage from a single API call."""

    def __init__(self, text: str, prompt_tokens: int = 0, completion_tokens: int = 0):
        self.text = text.strip()
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def __repr__(self) -> str:
        return (
            f"ApiCallResult(text_len={len(self.text)}, "
            f"prompt={self.prompt_tokens}, completion={self.completion_tokens})"
        )


def call_chat_completion(
    endpoint_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 1024,
    max_retries: int = 3,
    backoff_base: float = 2.0,
    role_label: str = "unknown",
) -> ApiCallResult:
    """
    Make a chat-completion request to any OpenAI-compatible endpoint.
    Implements retry with exponential backoff + jitter.

    Parameters
    ----------
    endpoint_url : str
        Base URL of the OpenAI-compatible API (e.g. https://api.fireworks.ai/inference/v1)
    api_key : str
        API key for authentication.
    model : str
        Model name or path.
    messages : list[dict]
        Chat messages in OpenAI format.
    temperature : float
        Sampling temperature (0.0 – 2.0).
    max_tokens : int
        Maximum tokens in the response.
    max_retries : int
        Number of retry attempts on failure.
    backoff_base : float
        Initial backoff in seconds (doubled each retry).
    role_label : str
        Human-readable label for logging (e.g. "Signal Analyst").
    """
    url = endpoint_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    last_error = None
    for attempt in range(1 + max_retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()

            # Extract text from OpenAI-format response
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            result = ApiCallResult(
                text=text,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
            )

            print(
                f"  [{role_label}] attempt={attempt+1}  "
                f"tokens={result.total_tokens}  "
                f"(prompt={result.prompt_tokens}, completion={result.completion_tokens})"
            )
            return result

        except (requests.RequestException, KeyError, json.JSONDecodeError) as e:
            last_error = e
            if attempt < max_retries:
                delay = backoff_base * (2 ** attempt) + random.uniform(0, 0.5)
                print(
                    f"  [{role_label}] attempt={attempt+1} FAILED — "
                    f"{e.__class__.__name__}: {e}.  Retrying in {delay:.1f}s …"
                )
                time.sleep(delay)
            else:
                print(
                    f"  [{role_label}] ALL RETRIES EXHAUSTED — "
                    f"{e.__class__.__name__}: {e}"
                )

    # All attempts failed — return an empty result so the pipeline can continue
    return ApiCallResult(
        text=f"[ERROR: {role_label} failed after {max_retries} retries: {last_error}]",
        prompt_tokens=0,
        completion_tokens=0,
    )