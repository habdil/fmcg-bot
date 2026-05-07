from __future__ import annotations

from typing import Any

import httpx

from chat_engine.ai.base import AIProvider


class AnthropicProvider(AIProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: int = 90,
        max_tokens: int = 1800,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.model)

    def generate_text(self, prompt: str) -> str:
        if not self.is_configured:
            raise RuntimeError("Anthropic provider is not configured.")

        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}],
        }
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        parts = [
            item.get("text", "")
            for item in data.get("content", [])
            if item.get("type") == "text" and item.get("text")
        ]
        text = "\n".join(parts).strip()
        if not text:
            raise RuntimeError("Anthropic returned an empty response.")
        return text
