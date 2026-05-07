from __future__ import annotations

import json
from typing import TypeVar

from pydantic import BaseModel

from chat_engine.ai.base import AIProvider

T = TypeVar("T", bound=BaseModel)


class GeminiProvider(AIProvider):
    def __init__(self, *, api_key: str, model: str, timeout_seconds: int = 90) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.model)

    def generate_text(self, prompt: str) -> str:
        if not self.is_configured:
            raise RuntimeError("Gemini provider is not configured.")

        from google import genai

        with genai.Client(api_key=self.api_key) as client:
            response = client.models.generate_content(model=self.model, contents=prompt)
        text = str(getattr(response, "text", "") or "").strip()
        if not text:
            raise RuntimeError("Gemini returned an empty response.")
        return text

    def generate_json(self, prompt: str, schema: type[T]) -> T:
        if not self.is_configured:
            raise RuntimeError("Gemini provider is not configured.")

        from google import genai
        from google.genai import types

        with genai.Client(api_key=self.api_key) as client:
            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                ),
            )
        if getattr(response, "parsed", None):
            return schema.model_validate(response.parsed)
        return schema.model_validate_json(json.dumps(response.text) if isinstance(response.text, dict) else response.text)
