from __future__ import annotations

import json
from typing import Any

import httpx

from src.core.config import settings


class AzureOpenAIClient:
    def __init__(self) -> None:
        self.endpoint = settings.azure_openai_endpoint.rstrip("/")
        self.deployment = settings.azure_openai_deployment
        self.api_version = settings.azure_openai_api_version
        self.api_key = settings.azure_openai_subscription_key

    @property
    def enabled(self) -> bool:
        return bool(self.endpoint and self.deployment and self.api_key)

    def chat(self, *, system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 1200) -> str:
        if not self.enabled:
            raise RuntimeError("Azure OpenAI is not configured")

        url = (
            f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions"
            f"?api-version={self.api_version}"
        )
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }
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


def parse_json_object(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        return {}

    # Try direct JSON first
    try:
        val = json.loads(text)
        if isinstance(val, dict):
            return val
    except json.JSONDecodeError:
        pass

    # Try fenced block extraction
    if "```" in text:
        parts = text.split("```")
        for p in parts:
            candidate = p.strip()
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
            try:
                val = json.loads(candidate)
                if isinstance(val, dict):
                    return val
            except json.JSONDecodeError:
                continue

    return {}
