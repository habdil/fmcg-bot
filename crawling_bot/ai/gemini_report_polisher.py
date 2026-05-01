from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from crawling_bot.config import settings

logger = logging.getLogger(__name__)


class GeminiReportPolish(BaseModel):
    final_text: str
    headline: str = ""
    analyst_summary: str = ""
    limitations: list[str] = Field(default_factory=list)


class GeminiReportPolisher:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model = model or settings.gemini_model

    def polish(self, structured_markdown: str) -> GeminiReportPolish:
        fallback = GeminiReportPolish(
            final_text=structured_markdown,
            headline=_first_non_empty_line(structured_markdown),
            analyst_summary="Rule-based structured response. Gemini polishing was not applied.",
            limitations=[],
        )
        if not self.api_key:
            return fallback

        try:
            from google import genai
            from google.genai import types

            prompt = (
                "You are a business intelligence writing assistant for FMCG sub-distributors.\n"
                "Rewrite the structured analysis into clear professional Bahasa Indonesia.\n"
                "Do not add new facts.\n"
                "Do not invent prices, sources, or causes.\n"
                "If data is missing, keep the limitation statement.\n"
                "Preserve numbers, dates, percentages, source counts, and confidence scores exactly.\n"
                "Make the response suitable for a Business Analyst who may rewrite it into a news brief.\n\n"
                "Structured analysis:\n"
                f"{structured_markdown}"
            )

            with genai.Client(api_key=self.api_key) as client:
                response = client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=GeminiReportPolish,
                    ),
                )
            if getattr(response, "parsed", None):
                return GeminiReportPolish.model_validate(response.parsed)
            return GeminiReportPolish.model_validate_json(response.text)
        except Exception as exc:  # pragma: no cover - network/API fallback path
            logger.warning("Gemini report polishing failed, using structured response: %s", exc)
            return fallback


def _first_non_empty_line(value: str) -> str:
    for line in value.splitlines():
        if line.strip():
            return line.strip()
    return ""
