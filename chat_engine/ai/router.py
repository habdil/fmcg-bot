from __future__ import annotations

from chat_engine.ai.anthropic_provider import AnthropicProvider
from chat_engine.ai.base import AIProvider, NoopAIProvider
from chat_engine.ai.gemini_provider import GeminiProvider
from chat_engine.ai.openai_provider import OpenAIProvider
from crawling_bot.config import settings


class AIRouter:
    def __init__(self) -> None:
        self._noop = NoopAIProvider()

    def guard_provider(self) -> AIProvider:
        return self._provider(settings.ai_fast_provider, fast=True)

    def planner_provider(self) -> AIProvider:
        return self._provider(settings.ai_primary_provider, fast=False)

    def extraction_provider(self) -> AIProvider:
        return self._provider(settings.ai_extraction_provider, fast=True, extraction=True)

    def composer_provider(self) -> AIProvider:
        return self._provider(settings.ai_primary_provider, fast=False)

    def reviewer_provider(self) -> AIProvider:
        return self._provider(settings.ai_review_provider, reviewer=True)

    def _provider(
        self,
        provider_name: str,
        *,
        fast: bool = False,
        reviewer: bool = False,
        extraction: bool = False,
    ) -> AIProvider:
        normalized = (provider_name or "").strip().lower()
        if normalized == "openai":
            model = (
                settings.openai_reviewer_model if reviewer and settings.openai_reviewer_model
                else settings.openai_extraction_model if extraction and settings.openai_extraction_model
                else settings.openai_fast_model if fast and settings.openai_fast_model
                else settings.openai_default_model
            )
            provider = OpenAIProvider(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=model,
                timeout_seconds=settings.ai_response_timeout_seconds,
                max_output_tokens=settings.openai_max_output_tokens,
                reasoning_effort=settings.openai_reasoning_effort,
            )
            return provider if provider.is_configured else self._noop
        if normalized == "anthropic":
            model = settings.anthropic_model_reviewer if reviewer else settings.anthropic_model_fast if fast else settings.anthropic_model_primary
            provider = AnthropicProvider(
                api_key=settings.anthropic_api_key,
                model=model,
                timeout_seconds=settings.ai_response_timeout_seconds,
            )
            return provider if provider.is_configured else self._noop
        if normalized == "gemini":
            model = settings.gemini_model_fast if fast else settings.gemini_model
            provider = GeminiProvider(
                api_key=settings.gemini_api_key,
                model=model,
                timeout_seconds=settings.ai_response_timeout_seconds,
            )
            return provider if provider.is_configured else self._noop
        return self._noop
