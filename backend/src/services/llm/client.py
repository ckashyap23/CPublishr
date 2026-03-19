"""
Unified LLM chat client.

Callers import `chat` and `is_enabled` from here.  The actual provider
(Azure OpenAI or standard OpenAI) is selected at runtime based on the
LLM_PROVIDER environment variable — callers never need to know which one
is in use.
"""
from __future__ import annotations

from typing import Any

import httpx

from src.core.config import settings
from src.services.llm.azure_openai import parse_json_object  # re-exported for callers

__all__ = ["chat", "is_enabled", "parse_json_object"]


def is_enabled() -> bool:
    """Return True if the configured LLM provider has all required credentials."""
    provider = _provider()
    if provider == "openai":
        return bool(settings.openai_api_key and settings.openai_model)
    # azure (default)
    return bool(
        settings.azure_openai_endpoint
        and settings.azure_openai_deployment
        and settings.azure_openai_subscription_key
    )


def chat(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 1200,
) -> str:
    """Send a chat prompt to the configured LLM and return the response text."""
    if not is_enabled():
        raise RuntimeError(
            f"LLM provider '{_provider()}' is not fully configured. "
            "Check your environment variables."
        )
    if _provider() == "openai":
        return _call_openai(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    return _call_azure(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _provider() -> str:
    return (settings.llm_provider or "azure").strip().lower()


def _call_azure(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> str:
    endpoint = settings.azure_openai_endpoint.rstrip("/")
    deployment = settings.azure_openai_deployment
    api_version = settings.azure_openai_api_version
    api_key = settings.azure_openai_subscription_key

    url = (
        f"{endpoint}/openai/deployments/{deployment}/chat/completions"
        f"?api-version={api_version}"
    )
    headers = {"api-key": api_key, "Content-Type": "application/json"}
    payload: dict[str, Any] = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": int(max_tokens),
    }

    with httpx.Client(timeout=45.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    return (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()


def _call_openai(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> str:
    api_key = settings.openai_api_key
    model = settings.openai_model

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": int(max_tokens),
    }

    with httpx.Client(timeout=45.0) as client:
        resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    return (data.get("choices") or [{}])[0].get("message", {}).get("content", "").strip()
