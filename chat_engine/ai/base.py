from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class AIProvider(ABC):
    @property
    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        raise NotImplementedError

    def generate_json(self, prompt: str, schema: type[T]) -> T:
        schema_prompt = (
            f"{prompt}\n\n"
            "Return only valid JSON matching this JSON schema. Do not wrap it in markdown.\n"
            f"{json.dumps(schema.model_json_schema(), ensure_ascii=False)}"
        )
        text = self.generate_text(schema_prompt)
        return schema.model_validate_json(_extract_json(text))


class NoopAIProvider(AIProvider):
    @property
    def is_configured(self) -> bool:
        return False

    def generate_text(self, prompt: str) -> str:
        raise RuntimeError("AI provider is not configured.")


def _extract_json(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return stripped[start : end + 1]
    raise ValueError("AI response did not contain a JSON object.")
