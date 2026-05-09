from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from chat_engine.ai.base import AIProvider

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)

_AUTH_DISABLED_UNTIL = 0.0
_AUTH_ERROR_LOGGED = False
_AUTH_DISABLE_SECONDS = 600


class OpenAIProvider(AIProvider):
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str,
        timeout_seconds: int = 90,
        max_output_tokens: int = 1200,
        reasoning_effort: str = "",
    ) -> None:
        self.api_key = api_key
        self.base_url = _normalize_base_url(base_url)
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_output_tokens = max_output_tokens
        self.reasoning_effort = reasoning_effort

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.model and time.monotonic() >= _AUTH_DISABLED_UNTIL)

    def generate_text(self, prompt: str) -> str:
        if not self.is_configured:
            raise RuntimeError("OpenAI provider is not configured.")

        payload = self._base_payload(prompt)
        data = self._post(payload)
        text = _response_text(data)
        if not text:
            raise RuntimeError("OpenAI returned an empty response.")
        return text

    def generate_json(self, prompt: str, schema: type[T]) -> T:
        if not self.is_configured:
            raise RuntimeError("OpenAI provider is not configured.")

        payload = self._base_payload(prompt)
        payload["text"] = {
            "format": {
                "type": "json_schema",
                "name": _schema_name(schema),
                "schema": schema.model_json_schema(),
                "strict": False,
            }
        }
        data = self._post(payload)
        return schema.model_validate_json(_response_text(data))

    def _base_payload(self, prompt: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "input": [{"role": "user", "content": prompt}],
            "max_output_tokens": self.max_output_tokens,
        }
        effort = self.reasoning_effort.strip().lower()
        if effort:
            payload["reasoning"] = {"effort": effort}
        return payload

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        started_at = time.perf_counter()
        try:
            response = httpx.post(
                f"{self.base_url}/responses",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            _log_request_metadata(
                data,
                model=self.model,
                latency_ms=_elapsed_ms(started_at),
            )
            return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {401, 403}:
                _disable_after_auth_error(self.model)
            else:
                logger.warning(
                    "AI request failed provider=openai model=%s latency_ms=%s status=%s error=%s",
                    self.model,
                    _elapsed_ms(started_at),
                    exc.response.status_code,
                    exc,
                )
            raise
        except Exception as exc:
            logger.warning(
                "AI request failed provider=openai model=%s latency_ms=%s error=%s",
                self.model,
                _elapsed_ms(started_at),
                exc,
            )
            raise


def _schema_name(schema: type[BaseModel]) -> str:
    name = re.sub(r"[^a-zA-Z0-9_-]+", "_", schema.__name__).strip("_")
    return (name or "response")[:64]


def _normalize_base_url(value: str) -> str:
    base_url = (value or "https://api.openai.com/v1").strip()
    return base_url.rstrip("/")


def _response_text(data: dict[str, Any]) -> str:
    direct = data.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    parts: list[str] = []
    for item in data.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []) or []:
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text:
                parts.append(text)
    text = "\n".join(parts).strip()
    if text:
        return text

    # Some API variants can return a top-level message-like content field.
    content = data.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
    return "\n".join(parts).strip()


def _elapsed_ms(started_at: float) -> int:
    return int((time.perf_counter() - started_at) * 1000)


def _log_request_metadata(data: dict[str, Any], *, model: str, latency_ms: int) -> None:
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    input_tokens = _usage_int(usage, "input_tokens", "prompt_tokens")
    output_tokens = _usage_int(usage, "output_tokens", "completion_tokens")
    total_tokens = _usage_int(usage, "total_tokens")
    cached_tokens = _cached_tokens(usage)
    response_model = str(data.get("model") or model)

    logger.info(
        "AI request provider=openai model=%s input_tokens=%s output_tokens=%s "
        "total_tokens=%s cached_tokens=%s latency_ms=%s",
        response_model,
        input_tokens,
        output_tokens,
        total_tokens,
        cached_tokens,
        latency_ms,
    )


def _usage_int(usage: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = usage.get(key)
        if isinstance(value, int):
            return value
    return None


def _cached_tokens(usage: dict[str, Any]) -> int | None:
    details = usage.get("input_tokens_details") or usage.get("prompt_tokens_details")
    if isinstance(details, dict) and isinstance(details.get("cached_tokens"), int):
        return details["cached_tokens"]
    return None


def _disable_after_auth_error(model: str) -> None:
    global _AUTH_DISABLED_UNTIL, _AUTH_ERROR_LOGGED
    _AUTH_DISABLED_UNTIL = time.monotonic() + _AUTH_DISABLE_SECONDS
    if not _AUTH_ERROR_LOGGED:
        logger.warning(
            "OpenAI authentication failed for model=%s. Disabling OpenAI calls for %s seconds; "
            "check OPENAI_API_KEY or set AI_*_PROVIDER to a configured provider.",
            model,
            _AUTH_DISABLE_SECONDS,
        )
        _AUTH_ERROR_LOGGED = True
