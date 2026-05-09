from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

from chat_engine.ai.openai_provider import OpenAIProvider


class _FakeResponse:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._data


class _SimpleJSON(BaseModel):
    answer: str


def test_openai_provider_uses_responses_api_for_text(monkeypatch, caplog) -> None:
    calls: list[dict[str, Any]] = []

    def fake_post(url, *, headers, json, timeout):  # noqa: ANN001
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _FakeResponse(
            {
                "model": "test-model",
                "output_text": "jawaban",
                "usage": {
                    "input_tokens": 123,
                    "output_tokens": 45,
                    "total_tokens": 168,
                    "input_tokens_details": {"cached_tokens": 12},
                },
            }
        )

    monkeypatch.setattr("chat_engine.ai.openai_provider.httpx.post", fake_post)

    provider = OpenAIProvider(api_key="test-key", model="test-model", timeout_seconds=12)

    with caplog.at_level(logging.INFO, logger="chat_engine.ai.openai_provider"):
        assert provider.generate_text("halo") == "jawaban"

    assert calls[0]["url"] == "https://api.openai.com/v1/responses"
    assert calls[0]["headers"]["Authorization"] == "Bearer test-key"
    assert calls[0]["json"]["model"] == "test-model"
    assert calls[0]["json"]["input"] == [{"role": "user", "content": "halo"}]
    assert calls[0]["timeout"] == 12
    assert "provider=openai" in caplog.text
    assert "model=test-model" in caplog.text
    assert "input_tokens=123" in caplog.text
    assert "output_tokens=45" in caplog.text
    assert "total_tokens=168" in caplog.text
    assert "cached_tokens=12" in caplog.text
    assert "latency_ms=" in caplog.text


def test_openai_provider_supports_custom_base_url(monkeypatch) -> None:
    calls: list[str] = []

    def fake_post(url, *, headers, json, timeout):  # noqa: ANN001
        calls.append(url)
        return _FakeResponse({"output_text": "ok"})

    monkeypatch.setattr("chat_engine.ai.openai_provider.httpx.post", fake_post)

    provider = OpenAIProvider(
        api_key="test-key",
        base_url="https://lb.jatevo.ai/v1/",
        model="test-model",
    )

    assert provider.generate_text("halo") == "ok"
    assert calls == ["https://lb.jatevo.ai/v1/responses"]


def test_openai_provider_uses_json_schema_for_structured_output(monkeypatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_post(url, *, headers, json, timeout):  # noqa: ANN001
        calls.append(json)
        return _FakeResponse(
            {
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": '{"answer":"ok"}'}],
                    }
                ]
            }
        )

    monkeypatch.setattr("chat_engine.ai.openai_provider.httpx.post", fake_post)

    provider = OpenAIProvider(api_key="test-key", model="test-model")
    result = provider.generate_json("buat json", _SimpleJSON)

    assert result.answer == "ok"
    assert calls[0]["text"]["format"]["type"] == "json_schema"
    assert calls[0]["text"]["format"]["name"] == "SimpleJSON"
    assert calls[0]["text"]["format"]["schema"]["title"] == "_SimpleJSON"
