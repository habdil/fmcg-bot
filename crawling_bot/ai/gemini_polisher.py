from __future__ import annotations

import json
import logging
from typing import Any

from chat_engine.ai.base import AIProvider, NoopAIProvider
from chat_engine.ai.router import AIRouter
from crawling_bot.processors.cleaner import fallback_summary
from crawling_bot.schemas.insight_schema import GeminiPolishedInsight, SourceReference
from crawling_bot.schemas.signal_schema import ExtractedSignal

logger = logging.getLogger(__name__)


class GeminiPolisher:
    """Article insight polisher routed through the active AI gateway."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        provider: AIProvider | None = None,
    ) -> None:
        # Passing api_key="" is supported for deterministic fallback tests.
        self.provider = provider or (NoopAIProvider() if api_key == "" else AIRouter().extraction_provider())

    def polish(
        self,
        *,
        title: str,
        clean_content: str,
        signals: list[ExtractedSignal],
        reason: str | None,
        evidence_text: str | None,
        source_references: list[SourceReference],
        urgency: str,
    ) -> GeminiPolishedInsight:
        fallback = self._fallback(title, clean_content, reason, evidence_text, urgency, source_references)

        payload: dict[str, Any] = {
            "title": title,
            "clean_content": clean_content[:4000],
            "signals": [signal.model_dump() for signal in signals],
            "reason": reason,
            "evidence_text": evidence_text,
            "source_references": [source.model_dump(mode="json") for source in source_references],
            "urgency": urgency,
        }
        prompt = (
            "Rewrite this extracted signal into a clear business insight for Indonesian UMKM owners. "
            "Do not add new facts. Use only the provided evidence. "
            "If a cause is not explicit, state that it is not clearly stated.\n\n"
            f"{json.dumps(payload, ensure_ascii=False)}"
        )

        if self.provider.is_configured:
            try:
                return self.provider.generate_json(prompt, GeminiPolishedInsight)
            except Exception as exc:
                logger.warning("AI polishing failed, using rule-based fallback: %s", exc)

        return fallback

    def _fallback(
        self,
        title: str,
        clean_content: str,
        reason: str | None,
        evidence_text: str | None,
        urgency: str,
        source_references: list[SourceReference],
    ) -> GeminiPolishedInsight:
        source_note = "; ".join(
            f"{source.source} - {source.title}" for source in source_references[:3]
        )
        return GeminiPolishedInsight(
            polished_title=title,
            polished_summary=fallback_summary(title, clean_content),
            business_reason=reason or "The article does not clearly state the direct business cause.",
            recommended_action=self._recommended_action(urgency),
            risk_level=urgency,
            source_note=source_note or "Source reference is attached in the article record.",
        )

    @staticmethod
    def _recommended_action(urgency: str) -> str:
        if urgency == "high":
            return "Monitor supplier availability, validate local stock, and prepare short-term mitigation."
        if urgency == "medium":
            return "Track the signal and compare it with related sources before changing procurement plans."
        return "Keep the insight as monitoring context."
