from __future__ import annotations

import json
import logging
from typing import Any

from crawling_bot.config import settings
from crawling_bot.processors.cleaner import fallback_summary
from crawling_bot.schemas.insight_schema import GeminiPolishedInsight, SourceReference
from crawling_bot.schemas.signal_schema import ExtractedSignal

logger = logging.getLogger(__name__)


class GeminiPolisher:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model = model or settings.gemini_model

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
        if not self.api_key:
            return fallback

        try:
            from google import genai
            from google.genai import types

            payload: dict[str, Any] = {
                "title": title,
                "clean_content": clean_content[:6000],
                "signals": [signal.model_dump() for signal in signals],
                "reason": reason,
                "evidence_text": evidence_text,
                "source_references": [source.model_dump(mode="json") for source in source_references],
                "urgency": urgency,
            }
            prompt = (
                "Rewrite this extracted signal into a clear business insight for FMCG "
                "sub-distributors. Do not add new facts. Use only the provided evidence. "
                "If a cause is not explicit, state that it is not clearly stated.\n\n"
                f"{json.dumps(payload, ensure_ascii=False)}"
            )

            with genai.Client(api_key=self.api_key) as client:
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=GeminiPolishedInsight,
                    ),
                )

            if getattr(response, "parsed", None):
                return GeminiPolishedInsight.model_validate(response.parsed)
            return GeminiPolishedInsight.model_validate_json(response.text)
        except Exception as exc:  # pragma: no cover - network/API fallback path
            logger.warning("Gemini polishing failed, using fallback summary: %s", exc)
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
